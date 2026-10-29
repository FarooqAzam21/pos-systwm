"""Add staff activation, security session versioning, and inventory manager role."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_staff_activation_rbac"
down_revision = "0008_secure_public_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the old Manager role valid for existing users. The new explicit role
    # is additive; no existing account is silently reassigned.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'INVENTORY_MANAGER'")
    op.add_column("users", sa.Column("is_activated", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "activation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending_approval", nullable=False),
        sa.Column("otp_hmac", sa.String(64)),
        sa.Column("otp_encrypted", sa.String(256)),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True)),
        sa.Column("otp_generated_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activation_business_status", "activation_requests", ["business_id", "status", "created_at"])
    op.create_index("ix_activation_user_status", "activation_requests", ["user_id", "status"])
    op.create_index(
        "uq_activation_open_user", "activation_requests", ["user_id"], unique=True,
        postgresql_where=sa.text("status IN ('pending_approval', 'otp_issued')"),
    )
    op.execute("ALTER TABLE public.activation_requests ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            REVOKE ALL ON TABLE public.activation_requests FROM anon;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            REVOKE ALL ON TABLE public.activation_requests FROM authenticated;
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("uq_activation_open_user", table_name="activation_requests")
    op.drop_index("ix_activation_user_status", table_name="activation_requests")
    op.drop_index("ix_activation_business_status", table_name="activation_requests")
    op.drop_table("activation_requests")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "token_version")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "is_activated")
    # PostgreSQL enum values cannot be safely removed without rewriting existing data.
