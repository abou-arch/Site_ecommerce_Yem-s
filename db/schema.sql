-- ===========================================================================
-- Yem's — Schéma de base (PostgreSQL)
--
-- Principe : une commande est une photographie. Les prix, noms et options
-- sont recopiés dans les lignes de commande au moment de l'achat. Si le
-- catalogue change demain, une commande passée hier garde ses montants.
--
-- À exécuter une fois :  psql "$DATABASE_URL" -f db/schema.sql
-- ===========================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────── clients

CREATE TABLE IF NOT EXISTS customers (
  id          BIGSERIAL PRIMARY KEY,
  phone       TEXT NOT NULL,               -- identifiant réel ici : le Mobile Money
  full_name   TEXT NOT NULL,
  email       TEXT,
  city        TEXT,
  country     TEXT NOT NULL DEFAULT 'BJ',  -- BJ, CI, TG, SN, NE — pays servis par KkiaPay
  is_vip      BOOLEAN NOT NULL DEFAULT FALSE,
  notes       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customers_phone_unique UNIQUE (phone)
);

COMMENT ON COLUMN customers.phone IS
  'Numéro au format international sans +, ex. 22997000000. Sert de clé métier.';

-- ────────────────────────────────────────────────────────────── commandes

-- Le cycle de vie d'une commande, du panier validé à la livraison.
DO $$ BEGIN
  CREATE TYPE order_status AS ENUM (
    'pending',     -- créée, paiement pas encore confirmé
    'to_confirm',  -- règlement hors ligne : l'atelier rappelle pour convenir
    'paid',        -- paiement vérifié auprès du prestataire
    'deposit',     -- acompte encaissé (sur-mesure), solde à la livraison
    'in_workshop', -- en production
    'shipped',
    'delivered',
    'cancelled',
    'refunded'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_kind AS ENUM ('standard', 'bespoke', 'mixed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Comment le client règle. Tant que l'atelier n'a pas de compte marchand
-- activé, tout passe par 'delivery' ou 'transfer' : la commande est bien
-- enregistrée, le règlement se convient sur WhatsApp.
DO $$ BEGIN
  CREATE TYPE payment_mode AS ENUM (
    'online',     -- widget du prestataire, vérifié côté serveur
    'delivery',   -- espèces ou Mobile Money à la remise
    'transfer'    -- transfert Mobile Money avant expédition
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS orders (
  id              BIGSERIAL PRIMARY KEY,
  reference       TEXT NOT NULL,            -- YMS-2608-0042, montré au client
  customer_id     BIGINT REFERENCES customers(id) ON DELETE SET NULL,
  status          order_status NOT NULL DEFAULT 'pending',
  kind            order_kind   NOT NULL DEFAULT 'standard',
  pay_mode        payment_mode NOT NULL DEFAULT 'online',

  -- Montants en francs CFA, entiers : le FCFA n'a pas de sous-unité,
  -- et un entier évite tout arrondi flottant sur les totaux.
  subtotal        INTEGER NOT NULL CHECK (subtotal >= 0),
  shipping        INTEGER NOT NULL DEFAULT 0 CHECK (shipping >= 0),
  total           INTEGER NOT NULL CHECK (total >= 0),
  amount_due      INTEGER NOT NULL CHECK (amount_due >= 0), -- ce qui est réclamé maintenant
  currency        TEXT    NOT NULL DEFAULT 'XOF',

  -- Livraison, recopiée telle que saisie
  ship_name       TEXT NOT NULL,
  ship_phone      TEXT NOT NULL,
  ship_address    TEXT NOT NULL,
  ship_city       TEXT NOT NULL,
  ship_country    TEXT NOT NULL DEFAULT 'BJ',
  ship_note       TEXT,

  notified_at     TIMESTAMPTZ,              -- WhatsApp envoyé au propriétaire
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT orders_reference_unique UNIQUE (reference),
  CONSTRAINT orders_total_coherent CHECK (total = subtotal + shipping)
);

CREATE INDEX IF NOT EXISTS orders_status_created_idx ON orders (status, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_customer_idx       ON orders (customer_id);

-- ───────────────────────────────────────────────────── lignes de commande

CREATE TABLE IF NOT EXISTS order_items (
  id            BIGSERIAL PRIMARY KEY,
  order_id      BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_slug  TEXT   NOT NULL,            -- loafer-ouidah, ou sur-mesure-derby
  name          TEXT   NOT NULL,            -- recopié : le catalogue peut changer
  unit_price    INTEGER NOT NULL CHECK (unit_price >= 0),
  qty           INTEGER NOT NULL CHECK (qty > 0),
  line_total    INTEGER NOT NULL CHECK (line_total >= 0),
  size          TEXT,
  color         TEXT,
  bespoke       JSONB,                      -- forme, cuir, semelle, pointure, initiales
  CONSTRAINT order_items_line_coherent CHECK (line_total = unit_price * qty)
);

CREATE INDEX IF NOT EXISTS order_items_order_idx ON order_items (order_id);

-- ─────────────────────────────────────────────────────────────── paiements

DO $$ BEGIN
  CREATE TYPE payment_status AS ENUM ('pending', 'success', 'failed', 'refunded');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS payments (
  id              BIGSERIAL PRIMARY KEY,
  order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  transaction_id  TEXT   NOT NULL,          -- identifiant KkiaPay
  status          payment_status NOT NULL DEFAULT 'pending',
  amount          INTEGER NOT NULL CHECK (amount >= 0),
  method          TEXT,                     -- momo, card, wallet
  provider        TEXT,                     -- MTN, Moov, Wave, Visa…
  payer_phone     TEXT,
  raw             JSONB,                    -- réponse KkiaPay intégrale, pour litige
  verified_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Une transaction KkiaPay ne doit être encaissée qu'une fois :
  -- c'est cette contrainte qui rend le webhook et la vérification idempotents.
  CONSTRAINT payments_transaction_unique UNIQUE (transaction_id)
);

CREATE INDEX IF NOT EXISTS payments_order_idx ON payments (order_id);

-- ──────────────────────────────────────────────── journal des changements

CREATE TABLE IF NOT EXISTS order_events (
  id         BIGSERIAL PRIMARY KEY,
  order_id   BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  label      TEXT   NOT NULL,               -- « paiement vérifié », « expédiée »…
  detail     JSONB,
  actor      TEXT,                          -- 'system', 'webhook', 'admin'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS order_events_order_idx ON order_events (order_id, created_at DESC);

-- ──────────────────────────────────────────────────────────────── livreurs

CREATE TABLE IF NOT EXISTS couriers (
  id         BIGSERIAL PRIMARY KEY,
  full_name  TEXT NOT NULL,
  phone      TEXT NOT NULL,
  zone       TEXT,                          -- Cotonou, Abidjan, Porto-Novo…
  active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT couriers_phone_unique UNIQUE (phone)
);

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS courier_id BIGINT REFERENCES couriers(id) ON DELETE SET NULL;

-- ─────────────────────────────────────────────── mise à jour de updated_at

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS orders_touch    ON orders;
DROP TRIGGER IF EXISTS customers_touch ON customers;

CREATE TRIGGER orders_touch    BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER customers_touch BEFORE UPDATE ON customers
  FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

COMMIT;
