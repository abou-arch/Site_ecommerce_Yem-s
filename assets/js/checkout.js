/* ===========================================================================
   Yem's — Panier et tunnel de commande

   Les montants affichés ici sont indicatifs : le serveur les recalcule à la
   création de la commande, et c'est SON total qui part au widget KkiaPay.
   Si les deux divergent, c'est le serveur qui a raison.
   =========================================================================== */
(function () {
  'use strict';

  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const cart = () => (window.YemsCart ? window.YemsCart.read() : []);
  const fmt = (n) => new Intl.NumberFormat('fr-FR').format(n) + ' F';

  const key = (i) => [i.id, i.size || '', i.color || '',
                      i.bespoke ? JSON.stringify(i.bespoke) : ''].join('|');

  /* ---------------------------------------------------------------- panier */

  const list = $('[data-cart-list]');

  function describe(item) {
    const bits = [item.color, item.size ? `pointure ${item.size}` : null];
    if (item.bespoke) {
      if (item.bespoke.sole) bits.push(`semelle ${item.bespoke.sole}`);
      if (item.bespoke.initials) bits.push(`initiales ${item.bespoke.initials}`);
    }
    return bits.filter(Boolean).join(' · ');
  }

  function renderCart() {
    if (!list) return;
    const items = cart();

    if (items.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <p class="display">Votre panier est vide.</p>
          <p class="text-muted">Les quatre lignes vous attendent — ou composez votre paire sur-mesure.</p>
          <div class="cta__actions" style="margin-top:var(--sp-5)">
            <a class="btn" href="chaussures.html">Voir les souliers</a>
            <a class="btn btn--ghost" href="configurateur.html">Composer ma paire</a>
          </div>
        </div>`;
      $$('[data-cart-summary]').forEach((el) => { el.hidden = true; });
      return;
    }

    list.innerHTML = items.map((item, index) => `
      <article class="line">
        <div class="line__body">
          <h2 class="line__name">${item.name}</h2>
          ${describe(item) ? `<p class="line__opts">${describe(item)}</p>` : ''}
          <p class="line__unit">${fmt(item.price)} l'unité</p>
        </div>
        <div class="line__qty">
          <button type="button" data-step="-1" data-index="${index}" aria-label="Retirer un exemplaire">−</button>
          <span aria-live="polite">${item.qty}</span>
          <button type="button" data-step="1" data-index="${index}" aria-label="Ajouter un exemplaire">+</button>
        </div>
        <p class="line__total">${fmt(item.price * item.qty)}</p>
        <button class="line__remove" type="button" data-remove="${index}"
                aria-label="Retirer ${item.name} du panier">Retirer</button>
      </article>`).join('');

    const subtotal = items.reduce((sum, i) => sum + i.price * i.qty, 0);
    $$('[data-cart-subtotal]').forEach((el) => { el.textContent = fmt(subtotal); });
    $$('[data-cart-summary]').forEach((el) => { el.hidden = false; });

    const bespoke = items.some((i) => i.bespoke);
    const notice = $('[data-deposit-notice]');
    if (notice) notice.hidden = !bespoke;
  }

  if (list) {
    list.addEventListener('click', (e) => {
      const step = e.target.closest('[data-step]');
      const remove = e.target.closest('[data-remove]');
      if (!step && !remove) return;

      const items = cart();
      if (step) {
        const i = Number(step.dataset.index);
        items[i].qty = Math.max(1, Math.min(20, items[i].qty + Number(step.dataset.step)));
      } else {
        items.splice(Number(remove.dataset.remove), 1);
      }
      window.YemsCart.write(items);
      renderCart();
    });
    renderCart();
  }

  /* -------------------------------------------------------------- checkout */

  const form = $('[data-checkout-form]');
  if (!form) return;

  const recap = $('[data-checkout-recap]');
  const status = $('[data-checkout-status]');
  const submit = $('[data-checkout-submit]');

  function renderRecap() {
    const items = cart();
    if (items.length === 0) {
      window.location.href = 'panier.html';
      return;
    }
    if (recap) {
      recap.innerHTML = items.map((i) => `
        <div class="spec-row">
          <dt>${i.qty} × ${i.name}${describe(i) ? `<br><small>${describe(i)}</small>` : ''}</dt>
          <dd>${fmt(i.price * i.qty)}</dd>
        </div>`).join('');
    }
    const subtotal = items.reduce((s, i) => s + i.price * i.qty, 0);
    $$('[data-cart-subtotal]').forEach((el) => { el.textContent = fmt(subtotal); });
  }
  renderRecap();

  function say(message, kind = 'info') {
    if (!status) return;
    status.textContent = message;
    status.dataset.kind = kind;
    status.hidden = !message;
  }

  let busy = false;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (busy) return;

    const data = Object.fromEntries(new FormData(form));
    busy = true;
    submit.disabled = true;
    say('Enregistrement de la commande…');

    let order;
    try {
      const res = await fetch('/api/orders/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...data, cart: cart() }),
      });
      order = await res.json();
      if (!res.ok || !order.ok) throw new Error(order.error || 'commande refusée');
    } catch (err) {
      busy = false;
      submit.disabled = false;
      say(err.message || 'Commande impossible. Réessayez ou écrivez-nous sur WhatsApp.', 'error');
      return;
    }

    if (!order.public_key) {
      busy = false;
      submit.disabled = false;
      say('Le paiement en ligne n\'est pas encore activé. Votre commande '
          + order.reference + ' est enregistrée — l\'atelier vous contacte.', 'error');
      return;
    }

    if (typeof window.openKkiapayWidget !== 'function') {
      busy = false;
      submit.disabled = false;
      say('Module de paiement indisponible. Rechargez la page.', 'error');
      return;
    }

    say(`Commande ${order.reference} — ouverture du paiement…`);

    // Le montant vient du serveur, jamais du panier local.
    window.openKkiapayWidget({
      amount: order.amount_due,
      key: order.public_key,
      sandbox: order.sandbox,
      position: 'center',
      theme: '#C9A46A',
      name: data.name,
      phone: data.phone,
      email: data.email || undefined,
      countries: ['BJ', 'CI', 'TG', 'SN', 'NE'],
      // repris par le webhook si le client ferme la page avant le retour
      data: JSON.stringify({ order_id: order.order_id }),
      partnerId: String(order.order_id),
    });

    window.addSuccessListener(async (response) => {
      say('Paiement reçu — vérification en cours…');
      try {
        const res = await fetch('/api/payments/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            order_id: order.order_id,
            transaction_id: response.transactionId,
          }),
        });
        const done = await res.json();
        if (!res.ok || !done.ok) throw new Error(done.error || 'vérification impossible');

        window.YemsCart.write([]);
        window.location.href = 'commande-confirmee.html?ref=' + encodeURIComponent(done.reference);
      } catch (err) {
        // L'argent est peut-être parti : surtout ne pas laisser croire à un échec sec.
        say('Paiement encaissé mais confirmation incomplète. Notez votre référence '
            + order.reference + ' et contactez l\'atelier sur WhatsApp.', 'error');
        busy = false;
        submit.disabled = false;
      }
    });

    window.addFailedListener(() => {
      busy = false;
      submit.disabled = false;
      say('Paiement interrompu. Votre panier est intact, vous pouvez réessayer.', 'error');
    });
  });
})();
