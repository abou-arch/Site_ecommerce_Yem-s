# Déploiement

Le site n'est plus hébergé sur GitHub Pages.

GitHub Pages ne sert que des fichiers statiques : il ne peut pas faire tourner
les fonctions serveur qui vérifient les paiements. Or la clé privée KkiaPay ne
doit jamais descendre dans le navigateur.

**→ Voir [`mise-en-ligne-cloudflare.md`](mise-en-ligne-cloudflare.md)** pour la
marche à suivre complète, et [`back-end.md`](back-end.md) pour l'architecture.

---

## Aperçu local, sans rien installer

Double-clique sur `index.html`. Pour un rendu strictement identique à la
production :

```bash
python -m http.server 8000
```

Puis **http://localhost:8000**. Les routes `/api/*` ne répondront pas — pour
les tester, il faut `npm run dev`.

---

## Le dépôt GitHub

Il reste utile comme historique et sauvegarde. Le déploiement, lui, part
directement de ta machine avec `npm run deploy`.

Si tu veux désactiver l'ancienne publication : **Settings → Pages → Source →
None**. Sinon les deux versions coexistent, et l'ancienne finira par dérouter
quelqu'un.
