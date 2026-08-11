# Déploiement — GitHub Pages

Dépôt : `abou-arch/Site_ecommerce_Yem-s` · branche `main` · **dépôt public**
URL finale : **https://abou-arch.github.io/Site_ecommerce_Yem-s/**

Le site est en HTML/CSS/JS pur, sans étape de build : GitHub Pages sert les
fichiers tels quels depuis la racine. Aucun workflow d'Actions n'est nécessaire.

---

## 1. Voir le site avant de le publier

Double-clique sur `index.html`. C'est tout — pas de serveur à lancer.

Une seule réserve : en `file://`, certains navigateurs bloquent des ressources.
Pour un aperçu strictement identique à la production :

```bash
# depuis le dossier du projet
python -m http.server 8000
```

Puis ouvre **http://localhost:8000**.

---

## 2. Pousser le commit

Le commit est déjà fait en local (`Homepage complète : design system, photos
normalisées, copy et animations`). Il reste à l'envoyer.

**Depuis GitHub Desktop** — le bouton « Push origin » suffit.

**Depuis un terminal, dans le dossier du projet :**

```bash
git push origin main
```

---

## 3. Activer GitHub Pages — trois clics, une seule fois

1. Ouvrir **https://github.com/abou-arch/Site_ecommerce_Yem-s/settings/pages**
2. Sous *Build and deployment* → **Source** : `Deploy from a branch`
3. **Branch** : `main`, dossier `/ (root)` → **Save**

Le premier déploiement prend une à deux minutes. L'URL apparaît en haut de la
même page une fois le site en ligne.

Le fichier `.nojekyll` à la racine désactive le traitement Jekyll : les fichiers
sont servis à l'identique, et le déploiement est plus rapide.

---

## 4. Après chaque modification

```bash
git add -A
git commit -m "Description de la modification"
git push
```

Pages se remet à jour tout seul en une minute environ. Si l'ancienne version
s'affiche encore, c'est le cache du navigateur : `Ctrl + Maj + R`.

---

## ⚠ À trancher : le cours et les photos sources sont déjà en ligne

Le commit précédent (`V1-sans le hero`, déjà poussé) contient :

- `course_all.txt` — le support de formation *Pen to Profit*, contenu sous droits
- les 8 photos WhatsApp d'origine — des produits d'autres marques

Le dépôt étant **public**, ces fichiers sont téléchargeables par n'importe qui
dès maintenant.

Le nouveau commit les retire du suivi et le `.gitignore` empêche qu'ils
reviennent — mais **cela ne les efface pas de l'historique**. Il faut réécrire
l'historique pour ça.

### La solution, si tu veux vraiment les faire disparaître

Le dépôt n'a que trois commits et aucun collaborateur : on peut repartir d'un
historique propre sans rien perdre du travail actuel.

```bash
# 1. Sauvegarde d'abord — au cas où
git branch sauvegarde-avant-nettoyage

# 2. Nouvelle racine, à partir de l'état actuel des fichiers suivis
git checkout --orphan propre
git add -A
git commit -m "Site Yem's — homepage complète"

# 3. Cette branche devient main
git branch -M propre main

# 4. Écrasement de l'historique distant
git push --force origin main
```

**Ce que ça fait** : ton travail actuel est intégralement conservé, mais les
trois anciens commits disparaissent — et avec eux le cours et les photos brutes.

**Ce que ça ne fait pas** : GitHub garde un temps les objets devenus
inaccessibles. Pour les purger immédiatement, ouvre un ticket de support GitHub
après le force-push.

**Avant de lancer ça**, vérifie que personne d'autre n'a cloné le dépôt : un
force-push casse les copies existantes.

### Si tu préfères ne rien réécrire

Passe le dépôt en privé — mais GitHub Pages sur un dépôt privé demande un
abonnement payant (Pro, Team ou Enterprise). Sur un compte gratuit, tu perdrais
l'hébergement.

---

## Rappel : ce qui reste à faire avant de montrer le site au client

- Le numéro WhatsApp de l'atelier (`22900000000`, 2 occurrences dans `index.html`)
- L'adresse e-mail (`contact@yems.example`)
- Les prix définitifs en FCFA
- Les trois témoignages, actuellement en « Prénom Nom »
- Les marques de fabricants tiers visibles sur `loafer-ouidah` et `loafer-ouidah-alt`

Le détail complet est dans le [README](../README.md).
