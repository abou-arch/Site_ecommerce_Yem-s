-- ===========================================================================
-- Yem's — Migration 002 : catalogue modifiable depuis l'atelier
--
-- À exécuter dans le SQL Editor de Neon, après schema.sql.
-- Elle est rejouable : chaque instruction porte IF NOT EXISTS.
-- ===========================================================================

-- ─── Corrections apportées au catalogue ────────────────────────────────────
--
-- Cette table ne DUPLIQUE pas le catalogue : elle le corrige. data/products.json
-- reste la source des noms, des textes longs, des pointures et des teintes ;
-- seuls les champs que l'atelier doit pouvoir changer seul vivent ici.
--
-- Un champ à NULL signifie « garder ce que dit le catalogue ». C'est ce qui
-- permet de revenir en arrière en effaçant simplement la valeur, sans avoir à
-- se souvenir du prix d'origine.
CREATE TABLE IF NOT EXISTS product_overrides (
  slug        TEXT PRIMARY KEY,

  price       INTEGER,        -- FCFA, entier : le franc CFA n'a pas de centime
  status      TEXT,           -- green | amber | red
  short       TEXT,           -- la phrase sous le nom, sur les vignettes
  images      JSONB,          -- [{file, w, h, alt}] ; [] = retirer les photos

  -- Retirer une pièce de la vente sans l'effacer. Supprimer vraiment un
  -- produit casserait l'historique des commandes qui le référencent : on le
  -- masque, les anciennes commandes restent lisibles.
  hidden      BOOLEAN NOT NULL DEFAULT FALSE,

  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by  TEXT NOT NULL DEFAULT 'admin'
);

CREATE INDEX IF NOT EXISTS idx_overrides_maj ON product_overrides (updated_at DESC);

-- Le prix doit rester un montant plausible. Une faute de frappe à 8 500 000 F
-- ou un prix négatif serait facturé tel quel par le serveur.
ALTER TABLE product_overrides
  DROP CONSTRAINT IF EXISTS overrides_prix_plausible;
ALTER TABLE product_overrides
  ADD CONSTRAINT overrides_prix_plausible
  CHECK (price IS NULL OR (price >= 500 AND price <= 5000000));

ALTER TABLE product_overrides
  DROP CONSTRAINT IF EXISTS overrides_statut_connu;
ALTER TABLE product_overrides
  ADD CONSTRAINT overrides_statut_connu
  CHECK (status IS NULL OR status IN ('green', 'amber', 'red'));

-- ─── Journal des modifications du catalogue ────────────────────────────────
--
-- Sans lui, personne ne peut répondre à « pourquoi ce soulier est passé de
-- 85 000 à 92 000 F ? ». Le journal garde l'ancienne et la nouvelle valeur.
CREATE TABLE IF NOT EXISTS catalog_events (
  id         BIGSERIAL PRIMARY KEY,
  slug       TEXT NOT NULL,
  champ      TEXT NOT NULL,
  avant      TEXT,
  apres      TEXT,
  actor      TEXT NOT NULL DEFAULT 'admin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_catalog_events_slug ON catalog_events (slug, created_at DESC);

-- ─── Traces d'anonymisation ────────────────────────────────────────────────
--
-- Quand l'atelier anonymise une commande livrée, les coordonnées du client
-- disparaissent mais la commande reste, pour la comptabilité. Ce drapeau dit
-- pourquoi les champs sont vides : sans lui, on croirait à une commande
-- incomplète.
ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS anonymized_at TIMESTAMPTZ;
