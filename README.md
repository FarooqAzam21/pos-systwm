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
5. Set `ACCESS_TOKEN_EXPIRE_MINUTES` and comma-separated `FRONTEND_ORIGINS`.
6. Copy root `.env.example` to `.env` if the frontend API URL differs from `http://localhost:8000`.

Never commit `.env` files or production secrets.

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

Vite runs at `http://localhost:5173`. To use a different API host, set `VITE_API_URL` in root `.env` and restart Vite.

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

Apply schema changes to the configured PostgreSQL database with `alembic upgrade head`.
