/**
 * merkle.js — PharmLedger
 * ========================
 * Algorithme identique à lots/merkle.py.
 * Format canonique : str(id)|batchNumber|drugName|manufacturer|productionDate|expiryDate|quantity
 * Encodage : UTF-8, hash : SHA-256 via WebCrypto API (résultat hex minuscules).
 *
 * Ce fichier s'exécute UNIQUEMENT dans le navigateur.
 * Le serveur ne peut pas influencer la vérification.
 */

// ─── Primitives ───────────────────────────────────────────────────────────────

async function sha256hex(str) {
  const bytes  = new TextEncoder().encode(str);          // UTF-8, comme Python .encode('utf-8')
  const buffer = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

async function hashPair(left, right) {
  return sha256hex(left + right);
}

const EMPTY_HASH_PROMISE = sha256hex('EMPTY');

// ─── Sérialisation (format canonique) ────────────────────────────────────────

function serializeDiplome(diplome) {
  // Doit correspondre EXACTEMENT à Diplome.serialize() en Python
  return [
    String(diplome.id),
    diplome.numeroEtudiant,
    diplome.nom,
    diplome.prenom,
    diplome.intitule,
    diplome.specialite,
    diplome.universite,
    diplome.faculte,
    diplome.dateObtention,  // YYYY-MM-DD
    diplome.mention,
  ].join('|');
}

// ─── Vérification de preuve ───────────────────────────────────────────────────

/**
 * Vérifie la preuve Merkle d'un lot dans le navigateur.
 * @param {object} lot      - Données brutes du lot (camelCase)
 * @param {object} proof    - { leafHash, path: [{siblingHash, direction}], root }
 * @param {string} trusted  - Root hash certifié (récupéré depuis /api/root/ au chargement)
 * @returns {object}        - { valid, reason, steps, computedRoot }
 */
async function verifyProof(diplome, proof, trusted) {
  const steps = [];

  // Étape 0 : recalculer le hash de la feuille depuis les données brutes
  const computedLeafHash = await sha256hex(serializeDiplome(diplome));

  if (computedLeafHash !== proof.leafHash) {
    return {
      valid: false,
      reason: 'Les données du diplôme ont été altérées (hash feuille invalide)',
      computedLeafHash,
      expectedLeafHash: proof.leafHash,
      steps: [],
      computedRoot: null,
    };
  }

  // Étapes 1..N : remonter l'arbre
  let current = computedLeafHash;
  for (let i = 0; i < proof.path.length; i++) {
    const { siblingHash, direction } = proof.path[i];
    const [left, right] = direction === 'right'
      ? [current, siblingHash]
      : [siblingHash, current];

    const output = await hashPair(left, right);
    steps.push({
      step:        i + 1,
      myHash:      current,
      siblingHash: siblingHash,
      direction:   direction,
      output:      output,
    });
    current = output;
  }

  const valid = current === trusted;
  return {
    valid,
    reason: valid ? 'Racine calculée = racine certifiée' : 'Racine calculée ≠ racine certifiée (falsification détectée)',
    steps,
    computedRoot: current,
    expectedRoot: trusted,
  };
}

// ─── Visualisation SVG de l'arbre Merkle ─────────────────────────────────────

/**
 * Dessine l'arbre Merkle dans un élément SVG.
 * @param {SVGElement} svg
 * @param {object}     treeData  - { nodes: [{level,index,hash,on_path,is_empty}], num_levels, num_leaves }
 * @param {number}     leafIndex - index de la feuille concernée (pour la colorer)
 * @param {string}     state     - 'idle' | 'verified' | 'failed'
 */
function drawMerkleTree(svg, treeData, leafIndex, state = 'idle') {
  svg.innerHTML = '';

  const { nodes, num_levels, num_leaves } = treeData;
  if (num_levels === 0) return;

  const W         = svg.clientWidth  || 800;
  const H         = svg.clientHeight || 340;
  const NODE_R    = Math.max(18, Math.min(28, Math.floor(W / (num_leaves * 3))));
  const PAD_X     = NODE_R * 2;
  const PAD_Y     = 36;
  const levelH    = (H - PAD_Y * 2) / Math.max(num_levels - 1, 1);

  // Coordonnées de chaque nœud : position (level, index) → {x, y}
  function nodePos(level, index) {
    const levelWidth = num_leaves / Math.pow(2, level);
    const cellW      = (W - PAD_X * 2) / levelWidth;
    const x          = PAD_X + cellW * (index + 0.5);
    // level 0 = feuilles (bas), level max = racine (haut)
    const y          = H - PAD_Y - level * levelH;
    return { x, y };
  }

  // Grouper les nœuds par level pour accès rapide
  const nodeMap = {};
  for (const n of nodes) {
    nodeMap[`${n.level},${n.index}`] = n;
  }

  // ── Dessiner les arêtes en premier (derrière les nœuds) ──────────────────
  for (const n of nodes) {
    if (n.level >= num_levels - 1) continue;  // La racine n'a pas de parent à dessiner

    const parent_level = n.level + 1;
    const parent_index = Math.floor(n.index / 2);
    const p1 = nodePos(n.level, n.index);
    const p2 = nodePos(parent_level, parent_index);

    const parentNode = nodeMap[`${parent_level},${parent_index}`];
    const onPath = n.on_path && parentNode && parentNode.on_path;

    let edgeClass = 'edge-default';
    if (onPath && state === 'verified') edgeClass = 'edge-verified';
    else if (onPath && state === 'failed')   edgeClass = 'edge-failed';
    else if (onPath)                         edgeClass = 'edge-on-path';

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', p1.x);
    line.setAttribute('y1', p1.y);
    line.setAttribute('x2', p2.x);
    line.setAttribute('y2', p2.y);
    line.setAttribute('class', edgeClass);
    svg.appendChild(line);
  }

  // ── Dessiner les nœuds ────────────────────────────────────────────────────
  for (const n of nodes) {
    const { x, y } = nodePos(n.level, n.index);
    const isRoot   = n.level === num_levels - 1;
    const isSelf   = n.level === 0 && n.index === leafIndex;

    let nodeClass = 'node-default';
    if (n.is_empty)          nodeClass = 'node-empty';
    else if (isRoot && state === 'verified') nodeClass = 'node-verified';
    else if (isRoot && state === 'failed')   nodeClass = 'node-failed';
    else if (isRoot)         nodeClass = 'node-root';
    else if (isSelf)         nodeClass = 'node-leaf-self';
    else if (n.on_path && state === 'verified') nodeClass = 'node-verified';
    else if (n.on_path && state === 'failed')   nodeClass = 'node-failed';
    else if (n.on_path)      nodeClass = 'node-on-path';

    // Cercle
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r',  NODE_R);
    circle.setAttribute('class', nodeClass);
    svg.appendChild(circle);

    // Hash tronqué (6 chars)
    if (!n.is_empty) {
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', x);
      label.setAttribute('y', y + 1);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('dominant-baseline', 'middle');
      label.setAttribute('font-size', Math.max(8, NODE_R * 0.48));
      label.setAttribute('font-family', 'monospace');
      label.setAttribute('fill', '#334155');
      label.textContent = n.hash.slice(0, 6) + '…';
      svg.appendChild(label);
    }

    // Label sous la feuille
    if (n.level === 0 && !n.is_empty) {
      const tag = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      tag.setAttribute('x', x);
      tag.setAttribute('y', y + NODE_R + 11);
      tag.setAttribute('text-anchor', 'middle');
      tag.setAttribute('font-size', 9);
      tag.setAttribute('fill', isSelf ? '#7c3aed' : '#94a3b8');
      tag.setAttribute('font-weight', isSelf ? 'bold' : 'normal');
      tag.textContent = isSelf ? '▶ ce lot' : `[${n.index}]`;
      svg.appendChild(tag);
    }

    // Label "ROOT" au-dessus de la racine
    if (isRoot) {
      const tag = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      tag.setAttribute('x', x);
      tag.setAttribute('y', y - NODE_R - 6);
      tag.setAttribute('text-anchor', 'middle');
      tag.setAttribute('font-size', 10);
      tag.setAttribute('font-weight', 'bold');
      tag.setAttribute('fill', state === 'verified' ? '#16a34a' : state === 'failed' ? '#dc2626' : '#b45309');
      tag.textContent = state === 'verified' ? '✓ ROOT' : state === 'failed' ? '✗ ROOT' : 'ROOT';
      svg.appendChild(tag);
    }
  }
}
