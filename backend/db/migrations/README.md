# Database Migrations

Recommended helper command:

```bash
scripts/db-migrate
```

Manual option (apply migrations in order):

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/db/migrations/0001_initial_schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/db/migrations/0002_seed_accounts.sql
```

Notes:
- `0001_initial_schema.sql` creates tables and constraints.
- `0002_seed_accounts.sql` inserts the provided chart of accounts.
