# Northstar POS & Inventory

A multi-tenant SaaS POS and inventory application built with React, Vite, FastAPI, SQLAlchemy, Alembic, and PostgreSQL. Each authenticated request is scoped to the business associated with the logged-in user.

## Project structure

```text
.
├── backend/
│   ├── alembic/                 # Versioned database migrations
│   ├── app/
│   │   ├── core/                # Settings and password/JWT security
│   │   ├── database/            # SQLAlchemy base/session
│   │   ├── dependencies/        # Authentication and role checks
│   │   ├── models/              # Tenant, inventory, and commerce models
│   │   ├── routers/             # REST endpoint modules
│   │   ├── schemas/             # Pydantic request/response contracts
│   │   └── services/            # Business and transaction logic
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── src/
│   ├── components/
│   ├── context/                 # Persistent session and toast state
│   ├── layouts/
│   ├── pages/
│   ├── routes/
│   └── services/                # Axios and domain API clients
├── .env.example
└── package.json
```

The Vite application is at the repository root; its source tree is `src/`.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.11+
- PostgreSQL 14+

## Configuration

1. Create a PostgreSQL database, for example `pos_system`.
2. Copy `backend/.env.example` to `backend/.env`.
3. Set `DATABASE_URL` to your PostgreSQL connection string using the `postgresql+psycopg://` driver form. URL-encode special characters in credentials.
4. Replace `SECRET_KEY` with a private random value of at least 32 characters.
5. Set `ACCESS_TOKEN_EXPIRE_MINUTES` and comma-separated `FRONTEND_ORIGINS` (include `https://pos-systwm.vercel.app` for the deployed frontend).
6. Copy root `.env.example` to `.env` if the frontend API URL differs from `http://localhost:8000`.

Never commit `.env` files or production secrets.

Migration `0008_secure_public_tables` enables row-level security on every existing table in the exposed `public` schema and revokes direct table/sequence privileges from Supabase's `anon` and `authenticated` roles. The POS frontend accesses data only through FastAPI, so it does not need direct PostgREST table access. The backend must continue connecting with the PostgreSQL owner role; that server-side role bypasses RLS. Public API roles receive no policies, so direct Supabase Data API access is denied by default. Enable RLS on any new public-schema tables as well.

## Run locally

### Backend

From the repository root, in PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive OpenAPI docs are at `http://localhost:8000/docs`.

### Frontend

In a second terminal, from the repository root:

```powershell
npm install
npm run dev
```

Vite runs at `http://localhost:5173`. In Vercel, set `VITE_API_URL` to `https://theorvion-pos-syst3m.onrender.com` and redeploy. In Render, set `FRONTEND_ORIGINS` to `https://pos-systwm.vercel.app,http://localhost:5173`. Set `VITE_API_URL` in root `.env` for local builds and restart Vite.

## Authentication and tenant isolation

- Registration creates a business and its first Owner user in one transaction. Login returns an expiring JWT access token.
- Passwords are hashed with Argon2. The frontend restores a session through `GET /auth/me`.
- The API derives the tenant from the authenticated user; clients cannot select a `business_id`.
- Customer, product, supplier, inventory, purchase, sale, payment, return, and dashboard reads and writes are tenant-scoped.
- User roles are Owner, Admin, Manager, and Cashier. Business profile editing is restricted to Owner/Admin; purchasing and inventory operations use role checks.
- The browser app uses bearer tokens in local storage. For deployment exposed to untrusted scripts, consider secure HttpOnly cookies and a CSRF strategy.

## Implemented modules

- Business registration, authentication, account/business settings, and protected dashboard.
- Inventory: categories, products, suppliers, opening stock, adjustments, stock movements, stock status, and inventory valuation.
- Customers: tenant-scoped customer records, balances, and customer history.
- Purchasing: supplier purchases, stock receipts, supplier payments, and weighted-average product costing.
- POS and sales: stock-checked checkout, invoice history, sale detail, payment status, and cashier records.
- Payments: sale payments and FIFO allocation of customer receipts to open sales.
- Returns: partial/full sale returns, inventory restoration, refunds, and return history.
- Dashboard: live sales, COGS, gross profit, inventory value, product rankings, payment methods, recent transactions, and date filtering.

Sales analytics are based on recorded transactions; there are no seeded/demo products or sales.

## API reference

All endpoints except `/health`, `/auth/register`, and `/auth/login` require:

```http
Authorization: Bearer <access_token>
```

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness response |
| `POST` | `/auth/register` | Create a business and Owner user |
| `POST` | `/auth/login` | Authenticate and return an access token |
| `GET`, `PUT` | `/auth/me` | Read/update the current account |
| `GET`, `PUT` | `/business` | Read/update the current business |
| `GET` | `/users`, `/users/{id}` | List/read users in the current business |
| `GET`, `POST` | `/categories` | List/create categories |
| `GET`, `PUT`, `DELETE` | `/categories/{id}` | Read/update/deactivate a category |
| `GET`, `POST` | `/products` | Search/list/create products |
| `GET`, `PUT`, `DELETE` | `/products/{id}` | Read/update/deactivate a product |
| `GET`, `POST` | `/suppliers` | List/create suppliers |
| `GET`, `PUT`, `DELETE` | `/suppliers/{id}` | Read/update/deactivate a supplier |
| `GET` | `/inventory` | Inventory totals and valuation |
| `GET` | `/inventory/low-stock`, `/inventory/out-of-stock` | Stock alerts |
| `GET` | `/inventory/{product_id}/movements` | Product stock history |
| `POST` | `/inventory/{product_id}/opening-stock` | Record opening stock |
| `POST` | `/inventory/{product_id}/adjust` | Adjust stock in/out |
| `GET`, `POST` | `/customers` | Search/list/create customers |
| `GET`, `PUT`, `DELETE` | `/customers/{id}` | Read/update/deactivate and view customer history |
| `GET`, `POST` | `/purchases` | List/create supplier purchases |
| `GET` | `/purchases/{id}` | Read a purchase |
| `GET`, `POST` | `/sales` | Search/list sales and complete a POS checkout |
| `GET` | `/sales/{id}` | Read sale, items, and payments |
| `GET` | `/sales/{id}/invoice/pdf` | Download a tenant-scoped PDF invoice |
| `POST`, `GET` | `/sales/{id}/returns` | Process/list returns for a sale |
| `GET` | `/returns` | List the current business's returns |
| `GET` | `/payments` | List tenant payments |
| `POST` | `/payments/customer` | Receive and allocate a customer payment |
| `POST` | `/payments/supplier` | Pay a supplier against a purchase balance |
| `GET` | `/dashboard/overview` | Live KPIs and date-filtered sales analytics |

Product listing accepts `search`, `category_id`, `low_stock`, `out_of_stock`, `active_only`, `page`, and `limit`. Most list endpoints are paginated.

Stock changes are committed with their corresponding stock movement in the same transaction. Product costs and selling prices use decimal monetary values; sale line costs are snapshotted for historical COGS. Returns restore the returned quantity and reverse the related sale value and COGS.

## Tests and build

```powershell
npm run lint
npm run build
```

Backend tests use an isolated SQLite test database; the application runtime uses PostgreSQL:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
python -m compileall -q app alembic tests
```

Apply schema changes to the configured PostgreSQL database with `alembic upgrade head`. Migration `0007` normalizes customer phones, consolidates records sharing a phone within a business, reattaches their sales/payments/audit references, preserves combined balances and adds a unique business-phone index. Apply it before deploying the API version that requires unique phone numbers.

## Staff roles and first-login activation

The server authorizes requests using the current user row and a centralized permission allow-list in `backend/app/dependencies/auth.py`. `Owner` has full workspace access and manages staff. `Cashier` can use checkout, read permitted sales and product details, and save customer contact information; cost and margin fields are withheld. `Inventory Manager` can manage catalog, stock, suppliers, and purchases, but not staff or financial reporting. Existing `Manager` accounts retain their inventory permissions and are not reassigned. Existing `Admin` accounts retain broad legacy access except staff and audit administration. All records continue to use the current single-business-per-user `business_id` model and are scoped on the backend.

Owners create staff from **Staff management** with a Gmail-address username, a temporary password, and Cashier or Inventory Manager role. Email suffix is validated but ownership is not verified; there is no configured email delivery. On the staff member's first login, the owner approves the pending request and generates or reveals the five-minute OTP in the owner dashboard's **Settings** page, then shares it privately out of band. The code is encrypted in the database for the owner-only reveal endpoint and independently HMAC-verified; it is single use and limited to five attempts. The staff member must set a new strong password before receiving a normal API token. The owner can reset a password or revoke sessions; generated temporary credentials are shown once in the authenticated owner UI and must be shared directly.

Access tokens remain bearer tokens in the existing frontend storage and are checked against a database token version on each protected request. Role changes, deactivation, password resets, and session revocation increment that version, immediately rejecting prior tokens. This preserves the existing stateless JWT/API contract while adding one database lookup per authenticated request. Activation encryption derives its key from `SECRET_KEY`; keep that production secret stable, because rotating it invalidates outstanding activation codes (and existing JWTs).

For deployment, back up PostgreSQL, deploy the migration before the new API, then deploy the backend and frontend:

```powershell
cd backend
alembic upgrade head
```

The new `0009_staff_activation_rbac` migration is additive: existing accounts are marked activated and do not have their role or password changed. It adds session-version and activation fields and a private `activation_requests` table with row-level security enabled and direct Supabase API roles revoked. Verify the migration revision with `alembic current` after applying it. No Redis environment variable is required for authorization; cache contents are never used to grant permissions. No OTP email provider is configured, so the owner-assisted delivery workflow is an explicit operational requirement.

## Optional Redis caching

The API can run without Redis. Set `REDIS_URL` on the backend to enable the shared Redis-compatible cache; PostgreSQL remains authoritative for all business data. Cached reads currently cover dashboard overview, report summaries and paginated reports, the category list, and business settings. Dashboard TTL is 30 seconds, reports and categories 60 seconds, and business settings 10 minutes (each cache entry receives up to 10% TTL jitter). Product and inventory quantities, transactions, payment balances, customers, and suppliers are intentionally not cached.

Mutations to sales, purchases, returns, payments, expenses, products, stock, categories, business settings, users, and daily closings advance scoped cache generations only after a successful SQLAlchemy commit. Rollbacks do not invalidate. Each request still authenticates and authorizes against PostgreSQL before reading cached data. Redis failures are logged and reads fall back to PostgreSQL; failures in the actual database loader still propagate. Logs include cache hit/miss/error/invalidation events and operation latency without cache keys or business data.

### Enable on Render

1. In the Render Dashboard select **New > Key Value**, choose a name, and select the same region and workspace as the backend web service. Choose a plan within your budget; free instances do not provide persistence, which is acceptable because this cache is disposable.
2. Wait for the instance to become **Available**, then open its **Connect** menu and copy the **Internal URL**. Render's internal URL uses `redis://` and is reachable by services in the same workspace and region. Use the internal URL; external access is unnecessary. If using an external connection for a non-Render backend, use the provider's `rediss://` TLS URL and restrict allowed IP ranges.
3. In the backend web service's **Environment** settings, add `REDIS_URL` with that copied internal URL. Do not put it in Vercel or commit it to Git. The remaining Redis settings are optional and default to conservative values in `backend/.env.example`.
4. Save changes and redeploy the backend. Startup attempts a Redis ping; if Redis is not ready or later becomes unavailable, the API remains available and logs a fallback warning.
5. Verify the deployment's `/health` response remains `{"status":"ok"}` and inspect backend logs for `cache_miss`, subsequent `cache_hit`, `cache_invalidation`, or `cache_*_error` events. `/health` intentionally does not reveal Redis status or infrastructure details.

Render Key Value provides Redis-compatible Valkey instances. Its internal URL is available from the instance's Connect menu; internal connections require the same workspace and region. See [Render Key Value documentation](https://render.com/docs/key-value) for current plan, authentication, and connection details.
