# BrewPass

BrewPass is a location-based coffee subscription platform. Subscribers buy a monthly coffee pass, discover nearby partner coffee shops on an interactive map, customize and place orders against their pass, and pick up their drinks by presenting a signed QR code. Shop owners manage incoming orders through a dedicated dashboard.

## Key Features

- **Phone-based authentication** — sign-up and login with a mobile number and one-time password (OTP), with role-based access for customers, shop owners and admins
- **Subscription plans** — tiered monthly passes with credit tracking, upgrade/downgrade, cancellation and monthly renewal
- **Mobile payment simulation** — checkout flow with success and failure scenarios and payment history
- **Shop discovery** — map view of nearby partner shops with distance, rating and open/closed filters
- **Ordering** — drink customization (size, milk, sugar, extra shots), order history and one-tap reorder
- **QR code pickup** — tamper-proof, signed QR codes verified by the shop at pickup
- **Shop owner dashboard** — order lifecycle management (accepted → preparing → ready → delivered)

## Tech Stack

| Layer    | Technology                                  |
| -------- | ------------------------------------------- |
| Backend  | Python, FastAPI                             |
| Database | PostgreSQL 16 + PostGIS                     |
| Frontend | React, TypeScript, Vite                     |
| Map      | Leaflet + OpenStreetMap                     |
| Tooling  | Docker Compose, Ruff, pytest, ESLint, Prettier |

See [ADR 0001](docs/adr/0001-tech-stack.md) for the reasoning behind these choices.

## Project Structure

```
backend/    FastAPI application (REST API under /api/v1)
frontend/   React + TypeScript web client
docs/adr/   Architecture Decision Records
```

## Getting Started

**Prerequisites:** Python 3.12+, Node.js 20+, Docker.

```bash
# 1. Configuration
cp .env.example .env

# 2. Database
docker compose up -d db

# 3. Backend — http://localhost:8000/api/v1/docs
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head        # create the schema
python -m app.db.seed       # load plans, demo users and Istanbul shops
uvicorn app.main:app --reload

# 4. Frontend — http://localhost:5173 (in a second terminal)
cd frontend
npm install
npm run dev
```

### Quality checks

Backend tests run against a real PostgreSQL database (`brewpass_test`, recreated on every run), so the `db` service must be up.

```bash
# Backend
cd backend && pytest && ruff check . && ruff format --check .

# Frontend
cd frontend && npm run lint && npm run format:check && npm run build
```

## Project Status

🚧 In active development.

## License

This project is licensed under the [MIT License](LICENSE).
