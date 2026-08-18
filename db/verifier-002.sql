-- ===========================================================================
-- Yem's — Contrôle de la migration 002
--
-- À coller dans le SQL Editor de Neon APRÈS avoir exécuté
-- migration-002-catalogue-editable.sql.
--
-- Cette requête ne modifie rien. Elle répond à une seule question : est-ce que
-- l'onglet Catalogue de l'écran d'administration va pouvoir enregistrer ?
--
-- Attendu : cinq lignes, toutes en « OK ».
-- Si l'une dit « MANQUE », la migration n'est pas passée en entier : relancez
-- le fichier complet, il est rejouable sans risque.
-- ===========================================================================

SELECT 'table product_overrides' AS controle,
       CASE WHEN to_regclass('public.product_overrides') IS NOT NULL
            THEN 'OK' ELSE 'MANQUE' END AS etat

UNION ALL SELECT 'table catalog_events',
       CASE WHEN to_regclass('public.catalog_events') IS NOT NULL
            THEN 'OK' ELSE 'MANQUE' END

UNION ALL SELECT 'garde-fou sur le prix',
       CASE WHEN EXISTS (SELECT 1 FROM pg_constraint
                         WHERE conname = 'overrides_prix_plausible')
            THEN 'OK' ELSE 'MANQUE' END

UNION ALL SELECT 'garde-fou sur le statut',
       CASE WHEN EXISTS (SELECT 1 FROM pg_constraint
                         WHERE conname = 'overrides_statut_connu')
            THEN 'OK' ELSE 'MANQUE' END

UNION ALL SELECT 'colonnes attendues',
       CASE WHEN (SELECT count(*) FROM information_schema.columns
                  WHERE table_name = 'product_overrides'
                    AND column_name IN ('slug','price','status','short',
                                        'images','hidden','updated_at')) = 7
            THEN 'OK' ELSE 'MANQUE' END;


-- ---------------------------------------------------------------------------
-- Essai à blanc, facultatif mais rassurant.
--
-- Écrit une correction bidon, vérifie que le garde-fou sur le prix mord, puis
-- efface tout. Aucune trace ne reste.
-- ---------------------------------------------------------------------------

-- 1. Une correction normale doit passer :
-- INSERT INTO product_overrides (slug, price) VALUES ('essai-a-blanc', 92000);

-- 2. Un prix aberrant doit être REFUSÉ par la base (erreur attendue) :
-- UPDATE product_overrides SET price = 8500000 WHERE slug = 'essai-a-blanc';

-- 3. Nettoyage :
-- DELETE FROM product_overrides WHERE slug = 'essai-a-blanc';
