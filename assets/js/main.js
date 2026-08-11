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
     4. Carrousel témoignages
     ---------------------------------------------------------------------- */
  const track = $('[data-tst-track]');

  if (track) {
    const slides = $$('.tst-slide', track);
    const dotsWrap = $('[data-tst-dots]');
    const prevBtn = $('[data-tst-prev]');
    const nextBtn = $('[data-tst-next]');
    let index = 0;
    let autoplayId = null;

    const dots = slides.map((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'tst-dot';
      dot.setAttribute('aria-label', `Témoignage ${i + 1}`);
      dot.addEventListener('click', () => { goTo(i); restartAutoplay(); });
      dotsWrap && dotsWrap.appendChild(dot);
      return dot;
    });

    function goTo(i) {
      index = (i + slides.length) % slides.length;
      track.style.transform = `translateX(-${index * 100}%)`;
      dots.forEach((d, n) => d.classList.toggle('is-active', n === index));
      slides.forEach((s, n) => s.setAttribute('aria-hidden', String(n !== index)));
    }

    function restartAutoplay() {
      if (reduceMotion) return;
      clearInterval(autoplayId);
      autoplayId = setInterval(() => goTo(index + 1), 7000);
    }

    prevBtn && prevBtn.addEventListener('click', () => { goTo(index - 1); restartAutoplay(); });
    nextBtn && nextBtn.addEventListener('click', () => { goTo(index + 1); restartAutoplay(); });

    // Support tactile
    let startX = 0;
    let delta = 0;
    track.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; delta = 0; }, { passive: true });
    track.addEventListener('touchmove',  (e) => { delta = e.touches[0].clientX - startX; }, { passive: true });
    track.addEventListener('touchend', () => {
      if (Math.abs(delta) > 45) { goTo(index + (delta < 0 ? 1 : -1)); restartAutoplay(); }
    });

    goTo(0);
    restartAutoplay();
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

  window.addEventListener('storage', (e) => { if (e.key === CART_KEY) refreshCartCount(); });
  refreshCartCount();

  // Exposé pour les futures pages produit / configurateur
  window.YemsCart = { read: readCart, refresh: refreshCartCount, KEY: CART_KEY };

  /* ----------------------------------------------------------------------
     6. Année courante dans le footer
     ---------------------------------------------------------------------- */
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
})();
