/* ==========================================================================
   YEM'S — Interactions globales
   Vanilla JS, aucune dépendance.
   ========================================================================== */
(function () {
  'use strict';

  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  /* ----------------------------------------------------------------------
     1. Header : état « collé » au scroll
     ---------------------------------------------------------------------- */
  const header = $('#header');

  if (header) {
    let ticking = false;
    const onScroll = () => {
      header.classList.toggle('is-stuck', window.scrollY > 24);
      ticking = false;
    };
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(onScroll);
        ticking = true;
      }
    }, { passive: true });
    onScroll();
  }

  /* ----------------------------------------------------------------------
     2. Menu mobile
     ---------------------------------------------------------------------- */
  const burger = $('.burger');
  const mobileMenu = $('#mobile-menu');

  if (burger && mobileMenu) {
    const setMenu = (open) => {
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
      mobileMenu.classList.toggle('is-open', open);
      document.body.classList.toggle('is-locked', open);
    };

    burger.addEventListener('click', () => {
      setMenu(burger.getAttribute('aria-expanded') !== 'true');
    });

    $$('a', mobileMenu).forEach((link) => {
      link.addEventListener('click', () => setMenu(false));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && mobileMenu.classList.contains('is-open')) {
        setMenu(false);
        burger.focus();
      }
    });

    // Referme si l'on repasse en desktop
    window.matchMedia('(min-width: 901px)').addEventListener('change', (e) => {
      if (e.matches) setMenu(false);
    });
  }

  /* ----------------------------------------------------------------------
     3. Révélation au scroll
     ---------------------------------------------------------------------- */
  const revealables = $$('[data-reveal]');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (revealables.length) {
    if (reduceMotion || !('IntersectionObserver' in window)) {
      revealables.forEach((el) => el.classList.add('is-visible'));
    } else {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

      revealables.forEach((el) => observer.observe(el));
    }
  }

  /* ----------------------------------------------------------------------
     5. Compteur panier (localStorage — partagé avec panier/checkout)
     ---------------------------------------------------------------------- */
  const CART_KEY = 'yems.cart';

  function readCart() {
    try {
      const raw = localStorage.getItem(CART_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function refreshCartCount() {
    const total = readCart().reduce((sum, item) => sum + (Number(item.qty) || 0), 0);
    $$('[data-cart-count]').forEach((el) => {
      el.textContent = String(total);
      el.hidden = total === 0 ? false : false; // toujours visible, à ajuster si besoin
      const link = el.closest('a');
      if (link) link.setAttribute('aria-label', `Panier (${total} article${total > 1 ? 's' : ''})`);
    });
  }

  function writeCart(items) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(items));
    } catch (err) {
      /* mode privé ou quota atteint : le panier ne persiste pas, le site reste utilisable */
    }
    refreshCartCount();
  }

  function addToCart(item) {
    const items = readCart();
    // même produit, même variante = on incrémente au lieu d'ajouter une ligne
    const key = (i) => [i.id, i.size || '', i.color || ''].join('|');
    const existing = items.find((i) => key(i) === key(item));
    if (existing) existing.qty += item.qty || 1;
    else items.push(Object.assign({ qty: 1 }, item));
    writeCart(items);
    return items;
  }

  window.addEventListener('storage', (e) => { if (e.key === CART_KEY) refreshCartCount(); });
  refreshCartCount();

  // Exposé pour les pages produit, le panier et le configurateur
  window.YemsCart = {
    read: readCart,
    write: writeCart,
    add: addToCart,
    refresh: refreshCartCount,
    KEY: CART_KEY,
  };

  /* ----------------------------------------------------------------------
     7. Fiche produit : sélecteurs et ajout au panier
     ---------------------------------------------------------------------- */
  function initPicker(selector, attr) {
    const buttons = $$(selector);
    if (!buttons.length) return null;

    // rien n'est présélectionné : le choix doit être explicite
    buttons.forEach((btn) => {
      btn.setAttribute('aria-pressed', 'false');
      btn.addEventListener('click', () => {
        buttons.forEach((b) => {
          b.classList.remove('is-active');
          b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('is-active');
        btn.setAttribute('aria-pressed', 'true');
      });
    });

    return () => {
      const active = buttons.find((b) => b.classList.contains('is-active'));
      return active ? active.dataset[attr] : null;
    };
  }

  const getSize = initPicker('.size', 'size');
  const getColor = initPicker('.swatch--btn', 'color');

  // l'intitulé « Choisissez une teinte » devient le nom du cuir retenu
  const colorLabel = $('[data-color-label]');
  if (colorLabel) {
    $$('.swatch--btn').forEach((btn) => {
      btn.addEventListener('click', () => { colorLabel.textContent = btn.dataset.color; });
    });
  }

  let toastEl = null;
  let toastTimer = null;

  function toast(message) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'toast';
      toastEl.setAttribute('role', 'status');
      document.body.appendChild(toastEl);
    }
    toastEl.innerHTML = message;
    // force un reflow pour que la transition rejoue à chaque appel
    void toastEl.offsetWidth;
    toastEl.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('is-visible'), 4200);
  }

  // le configurateur passe par cet événement plutôt que d'appeler toast() directement
  window.addEventListener('yems:toast', (e) => toast(e.detail.html));

  $$('[data-add-to-cart]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const size = getSize && getSize();
      const color = getColor && getColor();

      if (getSize && !size) { toast('Choisissez d\'abord une pointure.'); return; }
      if (getColor && !color) { toast('Choisissez d\'abord un cuir.'); return; }

      addToCart({
        id: btn.dataset.id,
        name: btn.dataset.name,
        price: Number(btn.dataset.price),
        size: size,
        color: color,
        qty: 1,
      });

      const label = btn.innerHTML;
      btn.setAttribute('data-added', '');
      btn.innerHTML = 'Ajouté au panier';
      setTimeout(() => {
        btn.removeAttribute('data-added');
        btn.innerHTML = label;
      }, 2200);

      const details = [btn.dataset.name, color, size].filter(Boolean).join(' · ');
      toast('<svg aria-hidden="true"><use href="#i-check"></use></svg>' +
            details + '. <a href="' + (btn.dataset.cart || 'panier.html') + '">voir le panier</a>');
    });
  });

  /* ----------------------------------------------------------------------
     6. Année courante dans le footer
     ---------------------------------------------------------------------- */
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
})();
