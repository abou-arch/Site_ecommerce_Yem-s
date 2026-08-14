/* ===========================================================================
   Yem's — Photos déposées par l'atelier

   Les fichiers vont dans un bucket R2. On n'y touche pas au contenu : un
   Worker ne sait pas redimensionner une image sans service payant, et une
   image réencodée à l'aveugle perdrait justement le grain du cuir qui fait
   vendre ces pièces.

   En revanche on LIT ses dimensions, parce que sans width et height dans le
   HTML, le navigateur ne réserve pas la place et la page saute au moment où
   la photo arrive. C'est exactement le défaut qu'on a évité partout ailleurs.
   =========================================================================== */

const TAILLE_MAX = 6 * 1024 * 1024;   // 6 Mo : une photo de téléphone y tient

/* ─────────────────────────────────────────────── dimensions, sans décodage */

function dimensionsPNG(v) {
  // Signature PNG puis chunk IHDR : largeur et hauteur en octets 16 à 23.
  if (v.getUint32(0) !== 0x89504e47) return null;
  return { w: v.getUint32(16), h: v.getUint32(20), type: 'image/png' };
}

function dimensionsJPEG(v) {
  if (v.getUint16(0) !== 0xffd8) return null;
  let i = 2;
  while (i < v.byteLength - 9) {
    if (v.getUint8(i) !== 0xff) { i += 1; continue; }
    const marqueur = v.getUint8(i + 1);
    // SOF0 à SOF15 portent les dimensions. C4, C8 et CC sont autre chose
    // (tables de Huffman, extensions) et doivent être sautés.
    const estSOF = marqueur >= 0xc0 && marqueur <= 0xcf
                && marqueur !== 0xc4 && marqueur !== 0xc8 && marqueur !== 0xcc;
    if (estSOF) {
      return { h: v.getUint16(i + 5), w: v.getUint16(i + 7), type: 'image/jpeg' };
    }
    if (marqueur === 0xd8 || (marqueur >= 0xd0 && marqueur <= 0xd9)) { i += 2; continue; }
    i += 2 + v.getUint16(i + 2);
  }
  return null;
}

function dimensionsWebP(v, octets) {
  const texte = (d, l) => String.fromCharCode(...octets.slice(d, d + l));
  if (texte(0, 4) !== 'RIFF' || texte(8, 4) !== 'WEBP') return null;
  const forme = texte(12, 4);
  if (forme === 'VP8X') {
    return { w: 1 + (octets[24] | (octets[25] << 8) | (octets[26] << 16)),
             h: 1 + (octets[27] | (octets[28] << 8) | (octets[29] << 16)),
             type: 'image/webp' };
  }
  if (forme === 'VP8L') {
    const b = octets[21] | (octets[22] << 8) | (octets[23] << 16) | (octets[24] << 24);
    return { w: (b & 0x3fff) + 1, h: ((b >> 14) & 0x3fff) + 1, type: 'image/webp' };
  }
  if (forme === 'VP8 ') {
    return { w: v.getUint16(26, true) & 0x3fff, h: v.getUint16(28, true) & 0x3fff,
             type: 'image/webp' };
  }
  return null;
}

/** Dimensions et type réel du fichier, lus dans ses premiers octets. */
export function inspecter(buffer) {
  const octets = new Uint8Array(buffer);
  const v = new DataView(buffer);
  if (buffer.byteLength < 32) return null;
  return dimensionsPNG(v) || dimensionsJPEG(v) || dimensionsWebP(v, octets);
}

/* ───────────────────────────────────────────────────────────── stockage */

/** Nom de fichier sûr, dérivé du slug. Aucune valeur venue du client n'entre
 *  dans le chemin : un nom libre permettrait d'écraser un autre objet. */
function nommer(slug, extension) {
  const propre = String(slug).toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 60);
  const jeton = Math.random().toString(36).slice(2, 8);
  return `${propre}-${Date.now().toString(36)}${jeton}.${extension}`;
}

const EXTENSIONS = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp' };

/**
 * Range une photo dans le bucket.
 * Rend { file, w, h } — ce que product_overrides.images attend.
 */
export async function deposer(bucket, slug, buffer) {
  if (!bucket) return { error: 'stockage des photos non configuré' };
  if (buffer.byteLength > TAILLE_MAX) {
    return { error: `photo trop lourde : ${Math.round(buffer.byteLength / 1024 / 1024)} Mo, 6 Mo maximum` };
  }

  // Le type est déduit du CONTENU, pas de l'en-tête envoyé par le navigateur :
  // un fichier peut se déclarer image/jpeg et contenir autre chose.
  const info = inspecter(buffer);
  if (!info) return { error: 'fichier illisible : envoyez un JPEG, un PNG ou un WebP' };
  if (info.w < 400 || info.h < 400) {
    return { error: `photo trop petite : ${info.w}×${info.h}, 400×400 minimum` };
  }

  const nom = nommer(slug, EXTENSIONS[info.type]);
  await bucket.put(`produits/${nom}`, buffer, {
    httpMetadata: {
      contentType: info.type,
      // Le nom contient un jeton aléatoire : le fichier ne change jamais de
      // contenu, il peut donc être mis en cache pour toujours.
      cacheControl: 'public, max-age=31536000, immutable',
    },
  });

  return { file: nom, w: info.w, h: info.h };
}

/** Sert une photo depuis le bucket. */
export async function servir(bucket, chemin) {
  if (!bucket) return null;
  // Un chemin remontant (« ../ ») sortirait du dossier prévu.
  if (!/^[a-z0-9][a-z0-9._-]{2,120}$/i.test(chemin)) return null;

  const objet = await bucket.get(`produits/${chemin}`);
  if (!objet) return null;

  return {
    corps: objet.body,
    type: objet.httpMetadata?.contentType || 'application/octet-stream',
    etag: objet.httpEtag,
  };
}
