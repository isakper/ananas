BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS accounts_active_name_unique_idx
  ON accounts ((LOWER(name)))
  WHERE is_active = TRUE;

COMMIT;
