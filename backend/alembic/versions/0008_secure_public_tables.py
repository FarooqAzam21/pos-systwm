"""Enable deny-by-default RLS on all tables in the exposed public schema."""

from alembic import op
import sqlalchemy as sa


revision = "0008_secure_public_tables"
down_revision = "0007_unique_customer_phones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The POS backend uses FastAPI JWT auth and a server-side PostgreSQL owner
    # connection, not Supabase PostgREST from the browser. With no API-role
    # policies, direct Data API access is denied by default. The PostgreSQL
    # table owner used by this backend continues to bypass RLS.
    op.execute(sa.text("""
        DO $$
        DECLARE target record;
        api_role text;
        BEGIN
            FOR target IN
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
                    target.schemaname,
                    target.tablename
                );
                FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                        EXECUTE format(
                            'REVOKE ALL PRIVILEGES ON TABLE %I.%I FROM %I',
                            target.schemaname,
                            target.tablename,
                            api_role
                        );
                    END IF;
                END LOOP;
            END LOOP;

            FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I',
                        api_role
                    );
                END IF;
            END LOOP;
        END
        $$;
    """))


def downgrade() -> None:
    # Do not disable RLS or restore broad grants automatically: that would
    # reopen public access to business data.
    pass
