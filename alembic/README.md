# Alembic

This project is structured to support Alembic migrations.

## Initialize locally

```bash
alembic init alembic
```

Then configure `sqlalchemy.url` in `alembic.ini` and import `Base.metadata` from `app.core.database`.
