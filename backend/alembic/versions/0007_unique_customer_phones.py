"""Merge customers that share a phone number and enforce unique numbers."""
from collections import defaultdict
import re

from alembic import op
import sqlalchemy as sa

revision = "0007_unique_customer_phones"
down_revision = "0006_supplier_purchase_orders"
branch_labels = None
depends_on = None


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _preserve_invalid_phone(bind, customer, original: str) -> None:
    note = f"Phone number removed during cleanup because it exceeded 11 digits: {original}"
    bind.execute(sa.text("""
        UPDATE customers
        SET phone = NULL,
            notes = CASE WHEN notes IS NULL OR notes = '' THEN :note ELSE notes || E'\\n' || :note END
        WHERE id = :customer_id
    """), {"note": note, "customer_id": customer["id"]})


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE customers SET phone=NULL WHERE phone IS NOT NULL AND phone=''"))
    customers = bind.execute(sa.text("""
        SELECT id, business_id, name, phone, email, address, city, tax_number,
               credit_limit, current_balance, notes, is_active, created_at
        FROM customers
        WHERE phone IS NOT NULL AND phone <> ''
        ORDER BY business_id, created_at, id
    """)).mappings().all()

    grouped = defaultdict(list)
    for customer in customers:
        phone = _digits(customer["phone"])
        if not phone:
            _preserve_invalid_phone(bind, customer, customer["phone"])
        elif len(phone) > 11:
            _preserve_invalid_phone(bind, customer, customer["phone"])
        else:
            grouped[(customer["business_id"], phone)].append(customer)

    for (business_id, phone), records in grouped.items():
        # Keep the active, oldest profile as the canonical customer.
        records.sort(key=lambda row: (not row["is_active"], row["created_at"], str(row["id"])))
        canonical = records[0]
        duplicate_ids = [row["id"] for row in records[1:]]
        combined_notes = list(dict.fromkeys(row["notes"].strip() for row in records if row["notes"] and row["notes"].strip()))
        merged = {
            "phone": phone,
            "email": canonical["email"] or next((row["email"] for row in records if row["email"]), None),
            "address": canonical["address"] or next((row["address"] for row in records if row["address"]), None),
            "city": canonical["city"] or next((row["city"] for row in records if row["city"]), None),
            "tax_number": canonical["tax_number"] or next((row["tax_number"] for row in records if row["tax_number"]), None),
            "credit_limit": max((row["credit_limit"] or 0 for row in records), default=0),
            "current_balance": sum((row["current_balance"] or 0 for row in records), 0),
            "notes": "\n\n".join(combined_notes) or None,
        }
        bind.execute(sa.text("""
            UPDATE customers SET phone=:phone, email=:email, address=:address, city=:city,
                tax_number=:tax_number, credit_limit=:credit_limit,
                current_balance=:current_balance, notes=:notes
            WHERE id=:customer_id
        """), {**merged, "customer_id": canonical["id"]})

        for duplicate_id in duplicate_ids:
            for table in ("sales", "payments"):
                bind.execute(sa.text(f"UPDATE {table} SET customer_id=:canonical WHERE business_id=:business AND customer_id=:duplicate"), {
                    "canonical": canonical["id"], "business": business_id, "duplicate": duplicate_id,
                })
            bind.execute(sa.text("""
                UPDATE audit_logs SET entity_id=:canonical
                WHERE business_id=:business AND entity_type='customer' AND entity_id=:duplicate_text
            """), {
                "canonical": str(canonical["id"]), "business": business_id,
                "duplicate_text": str(duplicate_id),
            })
            bind.execute(sa.text("DELETE FROM customers WHERE id=:duplicate AND business_id=:business"), {
                "duplicate": duplicate_id, "business": business_id,
            })

    op.create_index("uq_customers_business_phone", "customers", ["business_id", "phone"], unique=True)


def downgrade() -> None:
    # Merged customer rows cannot be split back without inventing history.
    op.drop_index("uq_customers_business_phone", table_name="customers")
