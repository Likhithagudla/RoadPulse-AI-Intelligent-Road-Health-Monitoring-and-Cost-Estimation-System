# 🗄️ RoadPulse AI – Database Migrations Guide

RoadPulse AI uses **Alembic** alongside **SQLAlchemy 2.0** for declarative schema versioning, automated migrations, and cross-database portability (SQLite and PostgreSQL).

---

## 1. Directory Structure

The database migrations framework is maintained inside `backend/`:
```
backend/
├── alembic.ini                   # Alembic environment and connection config
└── migrations/
    ├── env.py                    # Metadata bindings & migration execution script
    ├── script.py.mako            # Migration template
    └── versions/                 # Individual migration revision scripts
        └── 001_initial_schema.py # Initial baseline migration
```

---

## 2. Standard Migration Commands

All Alembic commands must be executed from inside the `backend/` directory with an active Python environment:

```bash
cd backend
```

### Apply All Pending Migrations (Upgrade to Latest)
```bash
alembic upgrade head
```

### View Migration History
```bash
alembic history --verbose
```

### Check Current Migration Version of the Database
```bash
alembic current
```

### Downgrade Database (Rollback by 1 Step)
```bash
alembic downgrade -1
```

### Downgrade Completely to Base State
```bash
alembic downgrade base
```

---

## 3. Creating New Schema Migrations

When modifying or adding models in `backend/app/models/`:

1. Edit or create the model file in `backend/app/models/`.
2. Ensure the model is imported in `backend/app/models/__init__.py`.
3. Generate an automated migration script comparing models against the database:
   ```bash
   alembic revision --autogenerate -m "add_column_name_to_table"
   ```
4. Inspect the generated revision file in `backend/migrations/versions/`.
5. Apply the migration:
   ```bash
   alembic upgrade head
   ```

---

## 4. Switching from SQLite to PostgreSQL

RoadPulse AI supports seamless switching between SQLite (local development) and PostgreSQL (production).

### Step 1: Update `.env` Connection URL
Edit `DATABASE_URL` in `.env` (or pass as an environment variable in container setups):
```ini
DATABASE_URL=postgresql://road_user:road_password@localhost:5432/road_ai
```

### Step 2: Ensure PostgreSQL Driver is Installed
Verify `psycopg2-binary` or `asyncpg` is installed:
```bash
pip install psycopg2-binary
```

### Step 3: Run Migrations Against PostgreSQL
```bash
cd backend
alembic upgrade head
```

### Step 4: Seed Initial Administrative Account
```bash
python seed_user.py
```

---

## 5. Migration Best Practices
* **Never alter existing applied migration files** in production branches. Generate a new revision script instead.
* **Always run unit & integration tests** against an in-memory database (`sqlite:///:memory:`) before applying schema migrations in production.
* **Backup production databases** before executing `alembic upgrade head`.
