"""
Moteur Merkle / DiploVerif
==========================
Même algorithme que static/js/merkle.js. Toute modification ici
doit être répercutée dans le fichier JS (et vice-versa).

Format canonique d'une feuille :
    SHA256( str(id) + "|" + numero_etudiant + "|" + nom + "|" + prenom + "|"
            + intitule + "|" + specialite + "|" + universite + "|"
            + faculte + "|" + date_obtention + "|" + mention )
    Encodage : UTF-8, sortie : hex minuscules.
"""

import hashlib


EMPTY_HASH = hashlib.sha256(b'EMPTY').hexdigest()


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hash_pair(left: str, right: str) -> str:
    return sha256(left + right)


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def build_tree(leaf_hashes: list[str]) -> list[list[str]]:
    if not leaf_hashes:
        return [[EMPTY_HASH]]

    size  = _next_power_of_two(len(leaf_hashes))
    level = leaf_hashes + [EMPTY_HASH] * (size - len(leaf_hashes))

    tree = [level]
    while len(level) > 1:
        level = [hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        tree.append(level)

    return tree


def get_root(tree: list[list[str]]) -> str:
    return tree[-1][0]


def generate_proof(tree: list[list[str]], leaf_index: int) -> list[dict]:
    proof = []
    index = leaf_index
    for level_idx in range(len(tree) - 1):
        level         = tree[level_idx]
        is_left_node  = index % 2 == 0
        sibling_index = index + 1 if is_left_node else index - 1
        proof.append({
            'sibling_hash':  level[sibling_index],
            'direction':     'right' if is_left_node else 'left',
            'level':         level_idx,
            'my_index':      index,
            'sibling_index': sibling_index,
        })
        index //= 2
    return proof


def verify_proof(leaf_hash: str, proof: list[dict], root: str) -> bool:
    current = leaf_hash
    for step in proof:
        if step['direction'] == 'right':
            current = hash_pair(current, step['sibling_hash'])
        else:
            current = hash_pair(step['sibling_hash'], current)
    return current == root


def rebuild_tree_from_db():
    from .models import MerkleLeaf
    leaves = list(MerkleLeaf.objects.order_by('leaf_index').select_related('diplome'))
    hashes = [leaf.leaf_hash for leaf in leaves]
    tree   = build_tree(hashes)
    return tree, leaves


def build_annual_tree(annee: int):
    """
    Construit l'arbre Merkle pour une année donnée (basé sur date_obtention).
    Retourne (tree, diplomes_list, leaf_hashes).
    """
    from .models import Diplome
    diplomes = list(
        Diplome.objects.filter(date_obtention__year=annee)
                       .order_by('id')
    )
    hashes = [d.compute_hash() for d in diplomes]
    tree   = build_tree(hashes)
    return tree, diplomes, hashes


def compute_and_store_annual_root(annee: int):
    """
    (Re)calcule la racine annuelle pour une année et la persiste dans AnnualRoot.
    Appelé après chaque nouvel ajout de diplôme.
    """
    from .models import AnnualRoot
    tree, diplomes, _ = build_annual_tree(annee)
    root = get_root(tree)
    AnnualRoot.objects.update_or_create(
        annee=annee,
        defaults={'root_hash': root, 'diploma_count': len(diplomes)},
    )
    return root


def tree_to_json(tree: list[list[str]], proof_leaf_index: int | None = None) -> dict:
    proof_indices = set()
    if proof_leaf_index is not None:
        idx = proof_leaf_index
        for lvl in range(len(tree)):
            proof_indices.add((lvl, idx))
            idx //= 2

    nodes = []
    for lvl_idx, level in enumerate(tree):
        for node_idx, node_hash in enumerate(level):
            nodes.append({
                'level':    lvl_idx,
                'index':    node_idx,
                'hash':     node_hash,
                'on_path':  (lvl_idx, node_idx) in proof_indices,
                'is_empty': node_hash == EMPTY_HASH,
            })

    return {
        'nodes':      nodes,
        'num_levels': len(tree),
        'num_leaves': len(tree[0]) if tree else 0,
    }
