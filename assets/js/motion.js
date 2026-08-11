/* ==========================================================================
   YEM'S — Motion
   Cinq gestes, aucune dépendance. Tout se désactive sous prefers-reduced-motion.
   ========================================================================== */
(function () {
  'use strict';

  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

  /* ----------------------------------------------------------------------
     2. Titres ligne par ligne
     Découpe le contenu sur les <br> et enveloppe chaque ligne dans un masque.
     Le balisage interne (italiques, accents) est conservé tel quel.
     ---------------------------------------------------------------------- */
  const headings = $$('[data-lines]');

  headings.forEach((el) => {
    // ces titres sont animés ici, pas par le révélateur générique de main.js
    el.removeAttribute('data-reveal');
    el.classList.add('is-visible');

    const parts = el.innerHTML
      .split(/<br\s*\/?>/i)
      .map((s) => s.trim())
      .filter(Boolean);

    if (parts.length === 0) return;

    el.innerHTML = parts
      .map((part, i) => `<span class="line"><span style="--i:${i}">${part}</span></span>`)
      .join('');

    if (reduce) el.classList.add('is-lines-in');
  });

  /* ----------------------------------------------------------------------
     4. Compteurs
     ---------------------------------------------------------------------- */
  function runCounter(el) {
    const target = parseFloat(el.dataset.count);
    if (Number.isNaN(target)) return;
    if (reduce) { el.textContent = String(target); return; }

    const dur = 1100;
    const t0 = performance.now();
    const step = (now) => {
      const p = clamp((now - t0) / dur);
      // même sortie que --ease-out-expo
      const eased = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
      el.textContent = String(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ----------------------------------------------------------------------
     Observateur commun : titres, photos, compteurs
     ---------------------------------------------------------------------- */
  const shots = $$('[data-shot]');
  const counters = $$('[data-count]');

  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;

        if (el.hasAttribute('data-lines')) el.classList.add('is-lines-in');
        if (el.hasAttribute('data-shot')) el.classList.add('is-shown');
        if (el.hasAttribute('data-count')) runCounter(el);

        io.unobserve(el);
      });
    }, { threshold: 0.2, rootMargin: '0px 0px -6% 0px' });

    [...headings, ...shots, ...counters].forEach((el) => io.observe(el));
  } else {
    headings.forEach((el) => el.classList.add('is-lines-in'));
    shots.forEach((el) => el.classList.add('is-shown'));
    counters.forEach((el) => { el.textContent = el.dataset.count; });
  }

  /* ----------------------------------------------------------------------
     1. Le fil de sellier qui se coud au scroll
     --seam va de 1 (rien de cousu) à 0 (couture terminée), piloté par la
     position de la couture dans la fenêtre.
     ---------------------------------------------------------------------- */
  const seams = $$('[data-seam]');

  if (seams.length && !reduce) {
    let queued = false;

    const drawSeams = () => {
      const vh = window.innerHeight;
      seams.forEach((seam) => {
        const r = seam.getBoundingClientRect();
        // 0 quand le haut de la couture atteint le bas de l'écran,
        // 1 quand son bas a franchi 35 % de la hauteur d'écran
        const progress = clamp((vh - r.top) / (r.height + vh * 0.65));
        seam.style.setProperty('--seam', String(1 - progress));
      });
      queued = false;
    };

    const onScroll = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(drawSeams);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    drawSeams();
  }

  /* ----------------------------------------------------------------------
     Vidéo hero : coupée si l'utilisateur refuse les animations
     ---------------------------------------------------------------------- */
  if (reduce) {
    $$('.hero__media video').forEach((v) => {
      v.removeAttribute('autoplay');
      v.pause();
    });
  }

  /* ----------------------------------------------------------------------
     5. Boutons magnétiques — pointeur précis uniquement
     ---------------------------------------------------------------------- */
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  if (finePointer && !reduce) {
    $$('.btn').forEach((btn) => {
      const RADIUS = 26;   // amplitude maximale du déplacement, en px

      const move = (e) => {
        const r = btn.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
        const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
        btn.style.setProperty('--mx', `${clamp(dx, -1, 1) * RADIUS * 0.34}px`);
        btn.style.setProperty('--my', `${clamp(dy, -1, 1) * RADIUS * 0.22}px`);
      };

      const reset = () => {
        btn.style.setProperty('--mx', '0px');
        btn.style.setProperty('--my', '0px');
      };

      btn.addEventListener('pointermove', move);
      btn.addEventListener('pointerleave', reset);
      btn.addEventListener('blur', reset);
    });
  }
})();
