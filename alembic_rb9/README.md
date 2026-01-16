# Alembic Migrations for rb9_db

This directory contains Alembic migrations for the `rb9_db` database, which uses **PascalCase** column naming convention.

## Database Configuration

The migrations connect to `rb9_db` using the connection settings from `src.core.config`:
- Uses `EXTERNAL_DATABASE_URL` property (which points to rb9_db)

## Directory Structure

```
alembic_rb9/
├── __init__.py
├── env.py              # Alembic environment configuration
├── script.py.mako      # Migration template
├── versions/           # Migration files
│   ├── __init__.py
│   └── 001_initial_create_all_tables.py
└── README.md           # This file
```

## Tables Created

The initial migration (`001_initial_create_all_tables.py`) creates the following tables:

1. **Timezones** - Timezone lookup table
2. **Lists** - Generic lookup table (for CaseType, Status, etc.)
3. **Users** - User accounts
4. **Cases** - Legal cases
5. **Jobs** - Job assignments

All tables use **PascalCase** column names (e.g., `CaseNo`, `UserNo`, `LastModified`).

## Usage

### Run Migrations

```bash
# Upgrade to latest version
alembic -c alembic_rb9.ini upgrade head

# Create a new migration
alembic -c alembic_rb9.ini revision -m "description"

# Downgrade one version
alembic -c alembic_rb9.ini downgrade -1

# Show current revision
alembic -c alembic_rb9.ini current

# Show migration history
alembic -c alembic_rb9.ini history
```

### First Time Setup

1. Make sure `rb9_db` database exists:
   ```sql
   CREATE DATABASE rb9_db;
   ```

2. Update connection settings in `src/core/config.py` or `ENVs/.env.local`:
   ```python
   EXTERNAL_DB_USER = "postgres"
   EXTERNAL_DB_PASSWORD = "your_password"
   EXTERNAL_DB_HOST = "localhost"
   EXTERNAL_DB_PORT = 5432
   EXTERNAL_DB_NAME = "rb9_db"
   ```

3. Run the initial migration:
   ```bash
   alembic -c alembic_rb9.ini upgrade head
   ```

## Important Notes

- **Column Naming**: All columns use PascalCase (e.g., `CaseNo`, `UserNo`, `LastModified`)
- **Relationships**: Foreign keys are defined with PascalCase column names
- **Extra Fields**: Some tables have extra fields that don't exist in `new_gls_db`
- **Type Differences**: Some fields have different types than `new_gls_db` (e.g., `CaseNumber` is VARCHAR in rb9_db, INTEGER in new_gls_db)

## Schema Differences from new_gls_db

### Users Table
- **Extra fields**: `PhoneNumber`, `Department`, `IsActive`, `LastLogin`
- **Same fields**: `UserNo`, `FullName`, `Email`, `LoginName`, `LoginPassword`, etc.

### Cases Table
- **Extra fields**: `CaseNumber` (VARCHAR vs INTEGER), `CourtName`, `JudgeName`, `CaseStatus`, `IsActive`
- **Type differences**: `CaseNumber` is VARCHAR(50) in rb9_db, INTEGER in new_gls_db
- **Relationships**: `CaseType` and `Status` reference `Lists` table

### Jobs Table
- **Extra fields**: `InternalNotes`, `Priority`, `EstimatedDuration`, `IsActive`
- **Type differences**: 
  - `CancelReason` is VARCHAR(100) in rb9_db, ENUM in new_gls_db
  - `SessionDuration` is VARCHAR(50) in rb9_db, VARCHAR(255) in new_gls_db
- **Relationships**: References `Cases`, `Timezones`, and `Users` tables

## Troubleshooting

### Connection Error
- Check database credentials in `src/core/config.py`
- Ensure `rb9_db` database exists
- Verify PostgreSQL is running

### Migration Already Applied
- Check current revision: `alembic -c alembic_rb9.ini current`
- If migration is already applied, you'll see an error. Use `downgrade` first if needed.

### Table Already Exists
- If tables already exist, you may need to:
  1. Drop existing tables manually, OR
  2. Modify the migration to use `op.create_table(..., if_not_exists=True)` (if supported)

