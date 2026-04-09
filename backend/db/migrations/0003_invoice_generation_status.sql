BEGIN;

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS generation_status TEXT NOT NULL DEFAULT 'uploaded'
  CHECK (generation_status IN ('uploaded', 'generating', 'ready', 'failed'));

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS generation_error TEXT;

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ;

COMMIT;
