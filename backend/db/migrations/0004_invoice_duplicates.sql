BEGIN;

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS content_hash TEXT;

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS duplicate_of_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS invoices_content_hash_idx
  ON invoices (content_hash);

CREATE INDEX IF NOT EXISTS invoices_duplicate_of_invoice_id_idx
  ON invoices (duplicate_of_invoice_id);

WITH ranked AS (
  SELECT
    id,
    FIRST_VALUE(id) OVER (
      PARTITION BY content_hash
      ORDER BY created_at ASC, id ASC
    ) AS first_id
  FROM invoices
  WHERE content_hash IS NOT NULL
)
UPDATE invoices target
SET duplicate_of_invoice_id = ranked.first_id
FROM ranked
WHERE target.id = ranked.id
  AND ranked.id <> ranked.first_id
  AND target.duplicate_of_invoice_id IS NULL;

COMMIT;
