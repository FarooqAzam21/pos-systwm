import json
import uuid

import pytest
from fastapi.testclient import TestClient
from redis import RedisError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models import Business, Category
from app.services import cache
from app.main import app
from app.core.config import settings


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expiries = {}
        self.fail = False

    def get(self, key):
        if self.fail:
            raise RedisError("offline")
        return self.values.get(key)

    def set(self, key, value, ex=None):
        if self.fail:
            raise RedisError("offline")
        self.values[key] = value
        self.expiries[key] = ex
        return True

    def delete(self, key):
        self.values.pop(key, None)

    def incr(self, key):
        self.values[key] = str(int(self.values.get(key, 0)) + 1)
        return int(self.values[key])


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache, "_client", client)
    return client


def test_cache_miss_populates_and_next_read_hits(fake_redis):
    calls = []
    load = lambda: calls.append(1) or {"amount": 12.5, "date": "2026-01-02"}
    first = cache.cached_response("reports", "biz-a", "Owner", {"start": "2026-01-01"}, 60, load)
    second = cache.cached_response("reports", "biz-a", "Owner", {"start": "2026-01-01"}, 60, load)
    assert first == second == {"amount": 12.5, "date": "2026-01-02"}
    assert len(calls) == 1
    assert next(iter(fake_redis.expiries.values())) in range(60, 67)


def test_scope_and_query_filters_produce_distinct_keys():
    base = cache.cache_key("reports", "biz-a", "Owner", {"page": 1})
    assert base != cache.cache_key("reports", "biz-b", "Owner", {"page": 1})
    assert base != cache.cache_key("reports", "biz-a", "Cashier", {"page": 1})
    assert base != cache.cache_key("reports", "biz-a", "Owner", {"page": 2})


def test_invalid_payload_is_deleted_and_reloaded(fake_redis):
    key = cache.cache_key("categories", "biz-a", "Owner", {}, 0)
    fake_redis.values[key] = "{invalid"
    assert cache.cached_response("categories", "biz-a", "Owner", {}, 30, lambda: ["fresh"]) == ["fresh"]
    assert json.loads(fake_redis.values[key]) == ["fresh"]


def test_redis_unavailable_falls_back_without_hiding_loader_errors(fake_redis):
    fake_redis.fail = True
    assert cache.cached_response("reports", "biz-a", "Owner", {}, 30, lambda: {"ok": True}) == {"ok": True}
    with pytest.raises(ValueError, match="database"):
        cache.cached_response("reports", "biz-a", "Owner", {}, 30, lambda: (_ for _ in ()).throw(ValueError("database")))


def test_application_starts_without_redis(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", None)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert app.state.redis_cache is None


def test_invalidation_runs_after_commit_and_not_after_rollback(monkeypatch):
    invalidations = []
    monkeypatch.setattr(cache, "invalidate_namespaces", lambda business_id, groups: invalidations.append((business_id, tuple(groups))))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine, expire_on_commit=False)
    business_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(Business(id=business_id, business_name="Test", owner_name="Owner", email="test@example.test"))
        session.commit()
        session.add(Category(business_id=business_id, name="Committed"))
        session.commit()
        assert any(entry[0] == str(business_id) and "categories" in entry[1] for entry in invalidations)
        prior = len(invalidations)
        session.add(Category(business_id=business_id, name="Rolled back"))
        session.flush()
        session.rollback()
        assert len(invalidations) == prior
    Base.metadata.drop_all(engine)
    engine.dispose()
