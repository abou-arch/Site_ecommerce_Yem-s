/* ===========================================================================
   Yem's — Réécriture des pages en bordure

   Le site reste entièrement statique : c'est ce qui le rend rapide sur une
   connexion mobile, et ce qui le rend lisible par Google. Mais l'atelier doit
   pouvoir changer un prix sans que personne ne reconstruise le site.

   HTMLRewriter résout exactement ça. Cloudflare fait défiler le HTML statique
   et n'en modifie que les éléments désignés, en flux, sans jamais charger la
   page entière en mémoire. Le coût est proche de zéro, et quand l'atelier n'a
   rien modifié, la réponse passe sans être touchée du tout.

   Le prix affiché et le prix facturé viennent du même endroit : les
   corrections lues en base. Ils ne peuvent pas diverger.
   =========================================================================== */

const STATUTS = {
  green: { cls: 'badge--green', court: 'Au Bénin',
           long: 'En stock à Cotonou, expédié sous 72 h' },
  amber: { cls: 'badge--amber', court: 'En route',
           long: 'En route, arrivage sous 10 jours' },
  red:   { cls: 'badge--red',   court: 'Indisponible',
           long: 'Sur commande uniquement' },
};

/** « 85 000 F », avec l'espace fine insécable du reste du site. */
function formaterPrix(valeur) {
  return String(Math.round(valeur)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' F';
}

const echapper = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/**
 * Applique les corrections de l'atelier à une réponse HTML.
 * Rend la réponse d'origine si rien n'a été modifié.
 */
export function reecrire(reponse, corrections) {
  const slugs = Object.keys(corrections || {});
  if (slugs.length === 0) return reponse;

  // Ne rien tenter sur autre chose que du HTML : une image qui passerait dans
  // HTMLRewriter serait corrompue.
  const type = reponse.headers.get('content-type') || '';
  if (!type.includes('text/html')) return reponse;

  let rewriter = new HTMLRewriter();

  for (const slug of slugs) {
    const c = corrections[slug];
    const eslug = slug.replace(/"/g, '');

    if (c.price != null) {
      rewriter = rewriter.on(`[data-prix="${eslug}"]`, {
        element(el) { el.setInnerContent(formaterPrix(c.price)); },
      });
    }

    if (c.short != null) {
      rewriter = rewriter.on(`[data-court="${eslug}"]`, {
        element(el) { el.setInnerContent(echapper(c.short)); },
      });
    }

    if (c.status != null && STATUTS[c.status]) {
      const st = STATUTS[c.status];
      rewriter = rewriter.on(`[data-badge="${eslug}"]`, {
        element(el) {
          // La classe porte la couleur : il faut retirer l'ancienne, sinon
          // une pièce passée en rupture garderait la pastille verte.
          const classes = (el.getAttribute('class') || '')
            .split(/\s+/).filter((k) => !k.startsWith('badge--'));
          classes.push(st.cls);
          el.setAttribute('class', classes.join(' '));

          const libelle = el.getAttribute('data-badge-long') === '1' ? st.long : st.court;
          el.setInnerContent(`<span class="badge__dot"></span>${libelle}`, { html: true });
        },
      });
    }

    // Une pièce retirée de la vente disparaît des grilles. Sa fiche reste
    // accessible par lien direct — un client qui a gardé l'onglet ouvert doit
    // comprendre pourquoi, pas tomber sur une erreur.
    if (c.hidden) {
      rewriter = rewriter.on(`[data-piece="${eslug}"]`, {
        element(el) { el.remove(); },
      });
    }

    if (Array.isArray(c.images) && c.images.length) {
      const [img] = c.images;
      rewriter = rewriter
        .on(`[data-piece="${eslug}"] img`, {
          element(el) {
            el.setAttribute('src', `/media/${img.file}`);
            el.setAttribute('width', String(img.w));
            el.setAttribute('height', String(img.h));
            if (img.alt) el.setAttribute('alt', img.alt);
          },
        })
        .on(`[data-piece="${eslug}"] source`, {
          // La source WebP d'origine ne correspond plus à la nouvelle photo :
          // la laisser ferait afficher l'ancienne image aux navigateurs
          // modernes, et la nouvelle aux autres.
          element(el) { el.remove(); },
        });
    }
  }

  return rewriter.transform(reponse);
}
