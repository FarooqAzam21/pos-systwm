"""Best-effort Redis cache for safe, serialized read responses."""
from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from collections.abc import Callable, Iterable
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis import Redis, RedisError
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)
_client: Redis | None = None


def create_redis_client() -> Redis | None:
    if not settings.redis_url:
        return None
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout_seconds,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        health_check_interval=30,
        max_connections=settings.redis_max_connections,
    )


def set_redis_client(client: Redis | None) -> None:
    global _client
    _client = client


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(jsonable_encoder(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cache_key(namespace: str, business_id: Any, role: str, filters: Any, generation: int = 0) -> str:
    return f"pos:v1:{namespace}:{business_id}:role:{role}:g:{generation}:q:{_fingerprint(filters)}"


def cached_response(
    namespace: str,
    business_id: Any,
    role: str,
    filters: Any,
    ttl: int,
    loader: Callable[[], Any],
) -> Any:
    """Return a cached JSON-safe value or run the loader; Redis errors fail open."""
    client = _client
    if client is None:
        return loader()
    base = f"pos:v1:version:{namespace}:{business_id}"
    started = time.perf_counter()
    try:
        generation = int(client.get(base) or 0)
        key = cache_key(namespace, business_id, role, filters, generation)
        payload = client.get(key)
        if payload is not None:
            try:
                value = json.loads(payload)
            except (TypeError, ValueError):
                client.delete(key)
                logger.warning("cache_invalid_payload namespace=%s", namespace)
            else:
                logger.info("cache_hit namespace=%s latency_ms=%.2f", namespace, (time.perf_counter() - started) * 1000)
                return value
    except RedisError:
        logger.warning("cache_read_error namespace=%s fallback=database", namespace, exc_info=True)
        return loader()

    logger.info("cache_miss namespace=%s latency_ms=%.2f", namespace, (time.perf_counter() - started) * 1000)
    value = loader()  # Database/application errors must propagate.
    try:
        serialized = json.dumps(jsonable_encoder(value), separators=(",", ":"), ensure_ascii=True)
        if len(serialized.encode("utf-8")) <= 1_000_000:
            # Jitter spreads expiration bursts while retaining a bounded lifetime.
            client.set(key, serialized, ex=max(1, int(ttl + random.uniform(0, max(1, ttl * 0.1)))))
    except (RedisError, TypeError, ValueError):
        logger.warning("cache_write_error namespace=%s", namespace, exc_info=True)
    return value


def invalidate_namespaces(business_id: Any, namespaces: Iterable[str]) -> None:
    client = _client
    if client is None or business_id is None:
        return
    for namespace in sorted(set(namespaces)):
        try:
            client.incr(f"pos:v1:version:{namespace}:{business_id}")
            logger.info("cache_invalidation namespace=%s", namespace)
        except RedisError:
            logger.warning("cache_invalidation_error namespace=%s", namespace, exc_info=True)


# Invalidate only after a successful commit. Rollbacks discard the pending changes.
_MODEL_NAMESPACES = {
    "Business": {"settings", "dashboard", "reports"},
    "Category": {"categories", "dashboard", "reports"},
    "Product": {"dashboard", "reports"},
    "StockMovement": {"dashboard", "reports"},
    "Sale": {"dashboard", "reports"}, "SaleItem": {"dashboard", "reports"},
    "SaleReturn": {"dashboard", "reports"}, "SaleReturnItem": {"dashboard", "reports"},
    "Purchase": {"dashboard", "reports"}, "PurchaseItem": {"dashboard", "reports"},
    "Payment": {"dashboard", "reports"}, "Customer": {"dashboard", "reports"},
    "Supplier": {"reports"}, "Expense": {"dashboard", "reports"},
    "ExpenseCategory": {"expense_categories", "reports"},
    "DailyClosing": {"reports"}, "User": {"users", "dashboard", "reports"},
}


def _scope_id(obj: Any) -> Any:
    business_id = getattr(obj, "business_id", None)
    if business_id is not None:
        return str(business_id)
    if obj.__class__.__name__ == "Business":
        return str(getattr(obj, "id", "")) or None
    return None


@event.listens_for(Session, "before_flush")
def _collect_invalidations(session: Session, _flush_context: Any, _instances: Any) -> None:
    pending: set[tuple[str, str]] = session.info.setdefault("redis_cache_invalidations", set())
    for obj in (*session.new, *session.dirty, *session.deleted):
        namespaces = _MODEL_NAMESPACES.get(obj.__class__.__name__)
        if not namespaces:
            continue
        if obj.__class__.__name__ == "User" and obj not in session.new and obj not in session.deleted:
            state = inspect(obj)
            if not any(state.attrs[name].history.has_changes() for name in ("role", "is_active", "full_name", "business_id") if name in state.attrs):
                continue
        business_id = _scope_id(obj)
        if business_id:
            pending.update((business_id, namespace) for namespace in namespaces)


@event.listens_for(Session, "after_commit")
def _apply_invalidations(session: Session) -> None:
    changes = session.info.pop("redis_cache_invalidations", set())
    for business_id, namespace in changes:
        invalidate_namespaces(business_id, (namespace,))


@event.listens_for(Session, "after_rollback")
def _discard_invalidations(session: Session) -> None:
    session.info.pop("redis_cache_invalidations", None)

