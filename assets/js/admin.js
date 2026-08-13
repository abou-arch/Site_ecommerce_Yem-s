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

  // Rechargement de la page dans le même onglet : on reprend où on en était.
  if (token()) ouvrir();
})();
