/* ==========================================================================
   YEM'S — Configurateur sur-mesure

   Le catalogue d'options est injecté dans la page par le générateur, sous
   forme de JSON (#cfg-data). Ce script ne fait que trois choses :
   suivre les choix, recalculer le total, et remettre le récapitulatif à jour.

   Le prix affiché est toujours recalculé depuis les données, jamais accumulé :
   un bug d'affichage ne peut donc pas devenir un bug de prix.
   ========================================================================== */
(function () {
  'use strict';

  const root = document.querySelector('[data-cfg]');
  if (!root) return;

  const dataEl = document.getElementById('cfg-data');
  if (!dataEl) return;

  const CFG = JSON.parse(dataEl.textContent);

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  /* ── état ───────────────────────────────────────────────────────────── */
  const choice = { shape: null, leather: null, sole: null, size: null, initials: '' };

  const find = (list, id) => CFG[list].find((o) => o.id === id) || null;

  function total() {
    const shape = find('shapes', choice.shape);
    if (!shape) return 0;
    let sum = shape.price;
    const leather = find('leathers', choice.leather);
    const sole = find('soles', choice.sole);
    if (leather) sum += leather.price;
    if (sole) sum += sole.price;
    if (choice.initials.trim()) sum += CFG.initials.price;
    return sum;
  }

  const fmt = (n) => n.toLocaleString('fr-FR').replace(/ | | /g, ' ') + ' F';

  /* ── rendu du récapitulatif ─────────────────────────────────────────── */
  function render() {
    const shape = find('shapes', choice.shape);
    const leather = find('leathers', choice.leather);
    const sole = find('soles', choice.sole);

    const lines = {
      shape:    shape   ? shape.name   : 'À choisir',
      leather:  leather ? leather.name : 'À choisir',
      sole:     sole    ? sole.name    : 'À choisir',
      size:     choice.size ? String(choice.size) : 'À choisir',
      initials: choice.initials.trim() || 'Aucune',
    };

    Object.keys(lines).forEach((key) => {
      const row = $('[data-line="' + key + '"]');
      if (!row) return;
      const value = $('[data-value]', row);
      if (value) value.textContent = lines[key];
      const chosen = lines[key] !== 'À choisir';
      row.toggleAttribute('data-empty', !chosen);
    });

    // suppléments affichés à côté de la ligne concernée
    const extra = (row, amount) => {
      const el = $('[data-extra]', row);
      if (el) el.textContent = amount ? '+ ' + fmt(amount) : '';
    };
    const rowLeather = $('[data-line="leather"]');
    const rowSole = $('[data-line="sole"]');
    const rowInit = $('[data-line="initials"]');
    if (rowLeather) extra(rowLeather, leather ? leather.price : 0);
    if (rowSole) extra(rowSole, sole ? sole.price : 0);
    if (rowInit) extra(rowInit, choice.initials.trim() ? CFG.initials.price : 0);

    const sum = total();
    $$('[data-total]').forEach((el) => {
      el.textContent = sum ? fmt(sum) : '…';
    });

    // aperçu : la photo du modèle retenu
    const shot = $('[data-cfg-shot]');
    if (shot) {
      if (shape && shape.image) {
        // Pas de photo tant que l'atelier n'a pas photographié sa production.
        shot.innerHTML = shape.image
          ? '<img src="' + CFG.base + 'assets/img/' + shape.image + '.jpg" alt="' + shape.name + '">'
          : '<span class="pshot__note">Photo à venir</span>';
        shot.classList.toggle('pshot--empty', !shape.image);
      } else {
        shot.innerHTML = '';
      }
    }

    // le bouton ne s'active que lorsque tout l'essentiel est décidé
    const ready = Boolean(shape && leather && sole && choice.size);
    $$('[data-cfg-add]').forEach((btn) => {
      btn.disabled = !ready;
      btn.setAttribute('aria-disabled', String(!ready));
    });
  }

  /* ── sélection d'une option ─────────────────────────────────────────── */
  $$('[data-group]').forEach((group) => {
    const key = group.dataset.group;
    $$('button[data-id]', group).forEach((btn) => {
      btn.addEventListener('click', () => {
        $$('button[data-id]', group).forEach((b) => b.setAttribute('aria-pressed', 'false'));
        btn.setAttribute('aria-pressed', 'true');
        choice[key] = key === 'size' ? Number(btn.dataset.id) : btn.dataset.id;
        render();
      });
    });
  });

  const initialsInput = $('[data-cfg-initials]');
  if (initialsInput) {
    initialsInput.addEventListener('input', () => {
      // 3 lettres maximum, sans chiffres ni ponctuation
      initialsInput.value = initialsInput.value
        .toUpperCase().replace(/[^A-ZÀ-Ö\s.]/g, '').slice(0, 4);
      choice.initials = initialsInput.value;
      render();
    });
  }

  /* ── ajout au panier ────────────────────────────────────────────────── */
  $$('[data-cfg-add]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      const shape = find('shapes', choice.shape);
      const leather = find('leathers', choice.leather);
      const sole = find('soles', choice.sole);

      const item = {
        id: 'sur-mesure-' + choice.shape,
        name: shape.name + ' sur-mesure',
        price: total(),
        size: choice.size,
        color: leather.name,
        bespoke: {
          shape: shape.id,
          leather: leather.id,
          sole: sole.id,
          size: choice.size,
          initials: choice.initials.trim(),
        },
        qty: 1,
      };

      if (window.YemsCart) window.YemsCart.add(item);

      const detail = [shape.name, leather.name, sole.name, 'pointure ' + choice.size,
                      choice.initials.trim()].filter(Boolean).join(' · ');
      const cart = btn.dataset.cart || 'panier.html';
      window.dispatchEvent(new CustomEvent('yems:toast', {
        detail: { html: '<svg aria-hidden="true"><use href="#i-check"></use></svg>' +
                        detail + '. <a href="' + cart + '">voir le panier</a>' },
      }));
    });
  });

  render();
})();
