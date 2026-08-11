-- ===========================================================================
-- Migration 001 — règlement hors ligne
--
-- À exécuter si le schéma a déjà été installé avant cette évolution.
-- Sur une base neuve, db/schema.sql suffit : il contient déjà tout ceci.
--
--   psql "$DATABASE_URL" -f db/migration-001-paiement-hors-ligne.sql
-- ===========================================================================

BEGIN;

-- Un atelier sans compte marchand doit pouvoir encaisser autrement.
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'to_confirm' AFTER 'pending';

DO $$ BEGIN
  CREATE TYPE payment_mode AS ENUM ('online', 'delivery', 'transfer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS pay_mode payment_mode NOT NULL DEFAULT 'online';

COMMIT;
