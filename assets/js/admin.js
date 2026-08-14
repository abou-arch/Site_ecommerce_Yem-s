/* ===========================================================================
   Yem's — Suivi des commandes, côté atelier

   Le jeton vit dans sessionStorage : il disparaît à la fermeture de l'onglet.
   localStorage aurait évité de le retaper chaque matin, mais il survit aux
   redémarrages et resterait lisible par n'importe quel script injecté dans la
   page. Pour un mot de passe qui donne accès aux coordonnées des clients,
   le confort ne vaut pas ça.
   =========================================================================== */
(function () {
  'use strict';

  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

  const gate = $('[data-gate]');
  if (!gate) return;

  const body = $('[data-body]');
  const list = $('[data-list]');
  const countEl = $('[data-count]');
  const errorEl = $('[data-gate-error]');
  const refresh = $('[data-refresh]');

  const CLE = 'yems.admin.token';
  let filtre = '';

  /* Les libellés que l'atelier comprend, en face des valeurs de la base. */
  const STATUTS = {
    pending:     { texte: 'En attente de paiement', ton: 'attente' },
    to_confirm:  { texte: 'À confirmer',            ton: 'urgent'  },
    deposit:     { texte: 'Acompte reçu',           ton: 'ok'      },
    paid:        { texte: 'Payée',                  ton: 'ok'      },
    in_workshop: { texte: 'En atelier',             ton: 'cours'   },
    shipped:     { texte: 'Expédiée',               ton: 'cours'   },
    delivered:   { texte: 'Livrée',                 ton: 'fini'    },
    cancelled:   { texte: 'Annulée',                ton: 'mort'    },
    refunded:    { texte: 'Remboursée',             ton: 'mort'    },
  };

  /* Ce qu'il est raisonnable de faire depuis un statut donné. Proposer les
     neuf à chaque fois inviterait à la fausse manœuvre. */
  const SUITES = {
    pending:     ['to_confirm', 'cancelled'],
    to_confirm:  ['deposit', 'paid', 'cancelled'],
    deposit:     ['in_workshop', 'refunded'],
    paid:        ['in_workshop', 'shipped', 'refunded'],
    in_workshop: ['shipped', 'cancelled'],
    shipped:     ['delivered'],
    delivered:   ['refunded'],
    cancelled:   [],
    refunded:    [],
  };

  const token = () => sessionStorage.getItem(CLE) || '';
  const fmt = (n) => new Intl.NumberFormat('fr-FR').format(n) + ' F';

  const echappe = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  function quand(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const jours = Math.floor((Date.now() - d) / 86400000);
    const date = d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' });
    const heure = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    if (jours === 0) return `aujourd'hui à ${heure}`;
    if (jours === 1) return `hier à ${heure}`;
    return `le ${date} à ${heure}`;
  }

  async function appel(chemin, options = {}) {
    const res = await fetch(chemin, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token(),
        ...(options.headers || {}),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) throw new Error('AUTH');
    if (!res.ok || !data.ok) throw new Error(data.error || 'réponse inattendue du serveur');
    return data;
  }

  /* ------------------------------------------------------------- affichage */

  function ligneArticle(a) {
    const options = [
      a.color, a.size ? `pointure ${a.size}` : null,
      a.bespoke ? 'sur-mesure' : null,
    ].filter(Boolean).join(' · ');
    return `<li><span>${a.qty} × ${echappe(a.name)}${
      options ? `<br><small>${echappe(options)}</small>` : ''
    }</span><span>${fmt(a.line_total)}</span></li>`;
  }

  function carte(o) {
    const st = STATUTS[o.status] || { texte: o.status, ton: 'attente' };
    const suites = SUITES[o.status] || [];
    const articles = Array.isArray(o.items) ? o.items : [];

    const relance = o.whatsapp_link
      ? `<a class="btn btn--sm" href="${echappe(o.whatsapp_link)}" target="_blank" rel="noopener">
           <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
           Prévenir le client
         </a>`
      : '';

    const avance = suites.length
      ? `<label class="cmd__next">
           <span class="visually-hidden">Faire passer la commande ${echappe(o.reference)} à</span>
           <select data-status="${o.id}">
             <option value="">Changer le statut…</option>
             ${suites.map((s) => `<option value="${s}">${STATUTS[s].texte}</option>`).join('')}
           </select>
         </label>`
      : '';

    return `<article class="cmd" data-order="${o.id}">
      <div class="cmd__top">
        <div>
          <h2 class="cmd__ref">${echappe(o.reference)}</h2>
          <p class="cmd__when">Passée ${quand(o.created_at)}${o.is_vip ? ' · <strong>client fidèle</strong>' : ''}</p>
        </div>
        <span class="cmd__status" data-ton="${st.ton}">${st.texte}</span>
      </div>

      <div class="cmd__grid">
        <div>
          <h3 class="cmd__label">Livrer à</h3>
          <p class="cmd__who">${echappe(o.ship_name)}</p>
          <p class="cmd__addr">${echappe(o.ship_address)}<br>${echappe(o.ship_city)}, ${echappe(o.ship_country)}</p>
          <p class="cmd__addr"><a href="tel:${echappe(o.ship_phone)}">${echappe(o.ship_phone)}</a></p>
          ${o.ship_note ? `<p class="cmd__note">« ${echappe(o.ship_note)} »</p>` : ''}
        </div>

        <div>
          <h3 class="cmd__label">Contenu</h3>
          <ul class="cmd__items">${articles.map(ligneArticle).join('')}</ul>
          <dl class="cmd__money">
            <div><dt>Livraison</dt><dd>${fmt(o.shipping)}</dd></div>
            <div><dt>Total</dt><dd>${fmt(o.total)}</dd></div>
            ${o.amount_due !== o.total
              ? `<div class="cmd__due"><dt>À encaisser d'abord</dt><dd>${fmt(o.amount_due)}</dd></div>`
              : ''}
          </dl>
        </div>
      </div>

      <div class="cmd__actions">${relance}${avance}</div>
      <p class="cmd__feedback" data-feedback hidden></p>
    </article>`;
  }

  function vide() {
    const quoi = filtre ? 'Aucune commande à ce statut.' : 'Aucune commande pour le moment.';
    return `<div class="empty-state">
      <p class="display">${quoi}</p>
      <p class="text-muted">Cette page se remplira toute seule dès la première commande passée sur le site.</p>
    </div>`;
  }

  /* ------------------------------------------------------------ chargement */

  async function charger() {
    list.setAttribute('aria-busy', 'true');
    try {
      const url = '/api/admin/orders' + (filtre ? '?status=' + encodeURIComponent(filtre) : '');
      const data = await appel(url);
      const commandes = data.orders || [];
      list.innerHTML = commandes.length ? commandes.map(carte).join('') : vide();
      countEl.textContent = commandes.length === 0 ? ''
        : commandes.length === 1 ? '1 commande' : `${commandes.length} commandes`;
    } catch (err) {
      if (err.message === 'AUTH') { deconnecter('Mot de passe refusé.'); return; }
      list.innerHTML = `<div class="empty-state">
        <p class="display">Impossible de charger les commandes.</p>
        <p class="text-muted">${echappe(err.message)}</p>
      </div>`;
      countEl.textContent = '';
    } finally {
      list.removeAttribute('aria-busy');
    }
  }

  function deconnecter(message) {
    sessionStorage.removeItem(CLE);
    body.hidden = true;
    refresh.hidden = true;
    gate.hidden = false;
    if (message) { errorEl.textContent = message; errorEl.hidden = false; }
  }

  function ouvrir() {
    gate.hidden = true;
    body.hidden = false;
    refresh.hidden = false;
    charger();
  }

  /* -------------------------------------------------------------- écoutes */

  gate.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    const saisi = new FormData(gate).get('token');
    sessionStorage.setItem(CLE, String(saisi).trim());
    try {
      await appel('/api/admin/orders?limit=1');
      gate.reset();
      ouvrir();
    } catch (err) {
      deconnecter(err.message === 'AUTH'
        ? 'Mot de passe refusé. Vérifiez qu\'il a bien été copié en entier.'
        : 'Le serveur ne répond pas : ' + err.message);
    }
  });

  $$('[data-filter]').forEach((chip) => {
    chip.addEventListener('click', () => {
      filtre = chip.dataset.filter;
      $$('[data-filter]').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
      charger();
    });
  });

  refresh.addEventListener('click', charger);

  list.addEventListener('change', async (e) => {
    const select = e.target.closest('[data-status]');
    if (!select || !select.value) return;

    const carteEl = select.closest('[data-order]');
    const retour = $('[data-feedback]', carteEl);
    const vise = select.value;
    select.disabled = true;

    try {
      await appel('/api/admin/orders', {
        method: 'POST',
        body: JSON.stringify({ order_id: Number(select.dataset.status), status: vise }),
      });
      retour.textContent = 'Statut mis à jour : ' + STATUTS[vise].texte.toLowerCase() + '.';
      retour.dataset.kind = 'ok';
      retour.hidden = false;
      setTimeout(charger, 700);
    } catch (err) {
      if (err.message === 'AUTH') { deconnecter('Session expirée.'); return; }
      retour.textContent = "Le changement n'a pas été enregistré : " + err.message;
      retour.dataset.kind = 'error';
      retour.hidden = false;
      select.disabled = false;
      select.value = '';
    }
  });


  /* ═══════════════════════════════════════════════════════════ onglets */

  const panneaux = {
    commandes: $('[data-panneau="commandes"]'),
    catalogue: $('[data-panneau="catalogue"]'),
  };
  let catalogueCharge = false;

  $$('[data-onglet]').forEach((bouton) => {
    bouton.addEventListener('click', () => {
      const vise = bouton.dataset.onglet;
      $$('[data-onglet]').forEach((b) =>
        b.setAttribute('aria-selected', String(b === bouton)));
      Object.entries(panneaux).forEach(([nom, el]) => { el.hidden = nom !== vise; });
      // Le catalogue ne se charge qu'à la première ouverture de son onglet :
      // inutile d'interroger la base pour quelqu'un venu voir ses commandes.
      if (vise === 'catalogue' && !catalogueCharge) chargerCatalogue();
    });
  });

  /* ═════════════════════════════════════════════════ ménage des commandes */

  const menage = $('[data-menage]');
  if (menage) {
    menage.addEventListener('submit', async (e) => {
      e.preventDefault();
      const retour = $('[data-menage-retour]');
      const avant = new FormData(menage).get('before');
      const bouton = $('button', menage);
      bouton.disabled = true;
      try {
        const r = await appel('/api/admin/orders/anonymize', {
          method: 'POST', body: JSON.stringify({ before: avant }),
        });
        retour.textContent = r.count === 0
          ? 'Aucune commande terminée avant cette date.'
          : `${r.count} commande${r.count > 1 ? 's' : ''} anonymisée${r.count > 1 ? 's' : ''}. Les montants sont conservés.`;
        retour.dataset.kind = 'ok';
        retour.hidden = false;
        charger();
      } catch (err) {
        if (err.message === 'AUTH') { deconnecter('Session expirée.'); return; }
        retour.textContent = "Le ménage n'a pas pu se faire : " + err.message;
        retour.dataset.kind = 'error';
        retour.hidden = false;
      } finally {
        bouton.disabled = false;
      }
    });
  }

  /* ═══════════════════════════════════════════════════════════ catalogue */

  const listeCatalogue = $('[data-catalogue]');

  const DISPOS = [
    ['green', 'Au Bénin, en stock'],
    ['amber', 'En route, sous 10 jours'],
    ['red', 'Indisponible, sur commande'],
  ];

  /* Les photos du dépôt sont référencées sans extension (« loafer-ouidah »)
     et servies depuis assets/img. Celles déposées par l'atelier portent leur
     extension et viennent de R2. Ce seul critère suffit à les distinguer. */
  const adressePhoto = (fichier) =>
    /\.(jpe?g|png|webp)$/i.test(fichier) ? `/media/${fichier}` : `assets/img/${fichier}.jpg`;

  function fichePiece(p) {
    const c = p.correction || {};
    const modifie = (champ) => (c[champ] != null && c[champ] !== '')
      ? '<span class="fiche__modifie">modifié</span>' : '';

    return `<article class="fiche" data-fiche="${echappe(p.slug)}">
      <div class="fiche__tete">
        <h2 class="fiche__nom">${echappe(p.name)}</h2>
        ${p.hidden ? '<span class="fiche__retire">Retiré de la vente</span>' : ''}
      </div>

      <form class="fiche__form" data-form="${echappe(p.slug)}">
        <label class="field">
          <span class="field__label">Prix ${modifie('price')}</span>
          <input type="number" name="price" inputmode="numeric" min="500" max="5000000"
                 step="500" value="${c.price ?? ''}" placeholder="${p.prix_catalogue}">
          <span class="field__hint">Vide = ${new Intl.NumberFormat('fr-FR').format(p.prix_catalogue)} F, le prix d'origine.</span>
        </label>

        <label class="field">
          <span class="field__label">Disponibilité ${modifie('status')}</span>
          <select name="status">
            <option value="">Valeur d'origine</option>
            ${DISPOS.map(([v, l]) =>
              `<option value="${v}"${c.status === v ? ' selected' : ''}>${l}</option>`).join('')}
          </select>
        </label>

        <label class="field field--large">
          <span class="field__label">Phrase de présentation ${modifie('short')}</span>
          <textarea name="short" rows="2" maxlength="240"
                    placeholder="${echappe(p.short_catalogue)}">${echappe(c.short || '')}</textarea>
        </label>

        <div class="fiche__photos">
          <span class="field__label">Photos</span>
          <div class="fiche__vignettes" data-vignettes="${echappe(p.slug)}">
            ${(p.images || []).map((im) =>
              `<img src="${echappe(adressePhoto(im.file))}" alt="" width="64" height="80" loading="lazy">`
            ).join('') || '<span class="fiche__vide">Aucune photo</span>'}
          </div>
          <label class="fiche__depot">
            <input type="file" accept="image/jpeg,image/png,image/webp" data-photo="${echappe(p.slug)}" hidden>
            <span>Ajouter une photo</span>
          </label>
          <span class="field__hint">JPEG, PNG ou WebP. 400×400 minimum, 6 Mo maximum.</span>
        </div>

        <div class="fiche__pied">
          <label class="fiche__retrait">
            <input type="checkbox" name="hidden"${p.hidden ? ' checked' : ''}>
            Retirer de la vente
          </label>
          <button class="btn btn--sm" type="submit">Enregistrer</button>
        </div>
        <p class="fiche__retour" data-retour hidden></p>
      </form>
    </article>`;
  }

  async function chargerCatalogue() {
    listeCatalogue.setAttribute('aria-busy', 'true');
    try {
      const data = await appel('/api/admin/catalogue');
      listeCatalogue.innerHTML = (data.produits || []).map(fichePiece).join('');
      catalogueCharge = true;

      const journal = $('[data-journal]');
      const liste = $('[data-journal-liste]');
      if ((data.journal || []).length) {
        liste.innerHTML = data.journal.map((e) => `<li>
          <strong>${echappe(e.slug)}</strong> · ${echappe(e.champ)} :
          ${echappe(e.avant ?? "valeur d'origine")} → ${echappe(e.apres ?? "valeur d'origine")}
          <span>${quand(e.created_at)}</span></li>`).join('');
        journal.hidden = false;
      }
    } catch (err) {
      if (err.message === 'AUTH') { deconnecter('Session expirée.'); return; }
      listeCatalogue.innerHTML = `<div class="empty-state">
        <p class="display">Catalogue indisponible.</p>
        <p class="text-muted">${echappe(err.message)}</p>
        <p class="text-muted">Si le message parle d'une table manquante, la migration
        002 n'a pas encore été exécutée dans Neon.</p>
      </div>`;
    } finally {
      listeCatalogue.removeAttribute('aria-busy');
    }
  }

  /* Enregistrement d'une fiche. Un champ vide renvoie null : c'est ce qui
     permet de revenir à la valeur du catalogue sans se souvenir de laquelle. */
  listeCatalogue.addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target.closest('[data-form]');
    if (!form) return;

    const slug = form.dataset.form;
    const d = new FormData(form);
    const retour = $('[data-retour]', form);
    const bouton = $('button[type="submit"]', form);
    bouton.disabled = true;

    const payload = {
      slug,
      price: d.get('price') === '' ? null : Number(d.get('price')),
      status: d.get('status') || null,
      short: d.get('short')?.trim() || null,
      hidden: d.get('hidden') === 'on',
    };

    try {
      await appel('/api/admin/catalogue', { method: 'POST', body: JSON.stringify(payload) });
      retour.textContent = 'Enregistré. La boutique affiche déjà la nouvelle valeur.';
      retour.dataset.kind = 'ok';
      retour.hidden = false;
      setTimeout(chargerCatalogue, 900);
    } catch (err) {
      if (err.message === 'AUTH') { deconnecter('Session expirée.'); return; }
      retour.textContent = err.message;
      retour.dataset.kind = 'error';
      retour.hidden = false;
    } finally {
      bouton.disabled = false;
    }
  });

  /* Dépôt d'une photo. Le fichier part brut, sans enveloppe multipart : sur un
     Worker, lire un multipart oblige à tout charger en mémoire. */
  listeCatalogue.addEventListener('change', async (e) => {
    const champ = e.target.closest('[data-photo]');
    if (!champ || !champ.files?.length) return;

    const slug = champ.dataset.photo;
    const fichier = champ.files[0];
    const form = $(`[data-form="${slug}"]`);
    const retour = $('[data-retour]', form);
    retour.textContent = `Envoi de ${fichier.name}…`;
    retour.dataset.kind = 'ok';
    retour.hidden = false;

    try {
      const r = await fetch(`/api/admin/media?slug=${encodeURIComponent(slug)}`, {
        method: 'POST',
        headers: { 'Content-Type': fichier.type, Authorization: 'Bearer ' + token() },
        body: fichier,
      });
      const data = await r.json().catch(() => ({}));
      if (r.status === 401) { deconnecter('Session expirée.'); return; }
      if (!r.ok || !data.ok) throw new Error(data.error || 'envoi refusé');

      // On repart des photos connues du serveur plutôt que de relire le DOM :
      // une vignette encore en cours de chargement donnerait des dimensions
      // nulles, qui seraient enregistrées telles quelles.
      const actuel = await appel('/api/admin/catalogue');
      const piece = (actuel.produits || []).find((x) => x.slug === slug);
      const anciennes = (piece?.correction?.images) || [];

      await appel('/api/admin/catalogue', {
        method: 'POST',
        body: JSON.stringify({
          slug,
          images: [{ ...data.photo, alt: `${slug.replace(/-/g, ' ')} — atelier Yem's` },
                   ...anciennes].slice(0, 6),
        }),
      });

      retour.textContent = `Photo ajoutée (${data.photo.w}×${data.photo.h}).`;
      champ.value = '';
      setTimeout(chargerCatalogue, 700);
    } catch (err) {
      retour.textContent = "La photo n'a pas été acceptée : " + err.message;
      retour.dataset.kind = 'error';
    }
  });

  // Rechargement de la page dans le même onglet : on reprend où on en était.
  if (token()) ouvrir();
})();
