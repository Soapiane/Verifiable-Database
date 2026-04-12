"""
Benchmark DiploVerif - mesures réelles sur le code de production.
Reproduit exactement les fonctions de merkle.py et models.py.
"""

import hashlib
import time
import statistics

# ─── Code de production (copié de merkle.py / models.py) ───────────────────

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

def build_tree(leaf_hashes: list) -> list:
    if not leaf_hashes:
        return [[EMPTY_HASH]]
    size  = _next_power_of_two(len(leaf_hashes))
    level = leaf_hashes + [EMPTY_HASH] * (size - len(leaf_hashes))
    tree  = [level]
    while len(level) > 1:
        level = [hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        tree.append(level)
    return tree

def get_root(tree: list) -> str:
    return tree[-1][0]

def generate_proof(tree: list, leaf_index: int) -> list:
    proof = []
    index = leaf_index
    for level_idx in range(len(tree) - 1):
        level         = tree[level_idx]
        is_left_node  = index % 2 == 0
        sibling_index = index + 1 if is_left_node else index - 1
        proof.append({
            'sibling_hash':  level[sibling_index],
            'direction':     'right' if is_left_node else 'left',
        })
        index //= 2
    return proof

def verify_proof(leaf_hash: str, proof: list, root: str) -> bool:
    current = leaf_hash
    for step in proof:
        if step['direction'] == 'right':
            current = hash_pair(current, step['sibling_hash'])
        else:
            current = hash_pair(step['sibling_hash'], current)
    return current == root

def serialize_diplome(d: dict) -> str:
    return '|'.join([
        str(d['id']),
        d['numero_etudiant'],
        d['nom'],
        d['prenom'],
        d['intitule'],
        d['specialite'],
        d['universite'],
        d['faculte'],
        d['date_obtention'],
        d['mention'],
    ])

def compute_hash(d: dict) -> str:
    return hashlib.sha256(serialize_diplome(d).encode('utf-8')).hexdigest()

# ─── Génération de données de test ─────────────────────────────────────────

MENTIONS = ['passable', 'assez_bien', 'bien', 'tres_bien', 'felicitations']
INTITULES = ['Master Informatique', 'Licence Mathematiques', 'Master MIAGE',
             'Licence Physique', 'Master Data Science']
SPECIALITES = ['Cybersecurite', 'Intelligence Artificielle', 'Reseaux',
               'Algebre', 'Big Data']

def make_diplome(i: int) -> dict:
    return {
        'id':              i,
        'numero_etudiant': f'ETU-2024-{i:04d}',
        'nom':             f'Etudiant{i:04d}',
        'prenom':          f'Prenom{i:04d}',
        'intitule':        INTITULES[i % len(INTITULES)],
        'specialite':      SPECIALITES[i % len(SPECIALITES)],
        'universite':      'Universite de Rennes',
        'faculte':         'UFR ISTIC',
        'date_obtention':  '2024-06-28',
        'mention':         MENTIONS[i % len(MENTIONS)],
    }

# ─── Utilitaires de mesure ──────────────────────────────────────────────────

def bench(fn, repeat=500):
    """Retourne (median_us, min_us, max_us)."""
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1e6)
    return statistics.median(times), min(times), max(times)

def bench_build(n, repeat=200):
    hashes = [compute_hash(make_diplome(i)) for i in range(n)]
    med, lo, hi = bench(lambda: build_tree(hashes), repeat=repeat)
    return med, lo, hi

def bench_proof(n, repeat=500):
    hashes = [compute_hash(make_diplome(i)) for i in range(n)]
    tree   = build_tree(hashes)
    med, lo, hi = bench(lambda: generate_proof(tree, n // 2), repeat=repeat)
    return med, lo, hi

def bench_verify(n, repeat=500):
    hashes   = [compute_hash(make_diplome(i)) for i in range(n)]
    tree     = build_tree(hashes)
    root     = get_root(tree)
    proof    = generate_proof(tree, n // 2)
    leaf_h   = hashes[n // 2]
    med, lo, hi = bench(lambda: verify_proof(leaf_h, proof, root), repeat=repeat)
    return med, lo, hi

# ─── Benchmarks ─────────────────────────────────────────────────────────────

print("=" * 70)
print("BENCHMARK DiploVerif - mesures sur le code de production")
print("=" * 70)

# 1. Sérialisation d'un diplôme
d = make_diplome(1)
s = serialize_diplome(d)
print(f"\nLongueur de serialisation : {len(s.encode('utf-8'))} octets")
print(f"Exemple : {s[:60]}...")

med, lo, hi = bench(lambda: serialize_diplome(d), repeat=2000)
print(f"\n[1] Serialisation d'un diplome")
print(f"    mediane = {med:.3f} µs   min = {lo:.3f} µs   max = {hi:.3f} µs")

# 2. Hachage d'un diplôme
med, lo, hi = bench(lambda: compute_hash(d), repeat=2000)
print(f"\n[2] Hachage SHA-256 d'un diplome (serialize + hash)")
print(f"    mediane = {med:.3f} µs   min = {lo:.3f} µs   max = {hi:.3f} µs")

# 3. hash_pair (noeud interne)
h1 = sha256("test_gauche")
h2 = sha256("test_droite")
med, lo, hi = bench(lambda: hash_pair(h1, h2), repeat=5000)
print(f"\n[3] hash_pair (noeud interne, 128 chars hex en entree)")
print(f"    mediane = {med:.3f} µs   min = {lo:.3f} µs   max = {hi:.3f} µs")

# 4. Construction de l'arbre pour différentes tailles
print(f"\n[4] Construction de l'arbre build_tree(n)")
print(f"    {'n':>6}  {'n_padded':>9}  {'hauteur':>8}  {'mediane':>10}  {'min':>8}  {'max':>8}")
for n in [10, 50, 100, 300, 500, 1000, 5000]:
    n_pad = _next_power_of_two(n)
    h     = n_pad.bit_length() - 1
    rep   = max(50, 500 // (n // 10 + 1))
    med, lo, hi = bench_build(n, repeat=rep)
    print(f"    {n:>6}  {n_pad:>9}  {h:>8}  {med:>9.1f}µs  {lo:>6.1f}µs  {hi:>6.1f}µs")

# 5. Génération de preuve
print(f"\n[5] Generation de preuve generate_proof(tree, i)")
print(f"    {'n':>6}  {'hauteur':>8}  {'elements_preuve':>16}  {'mediane':>10}  {'min':>8}")
for n in [10, 50, 100, 300, 1000, 5000]:
    n_pad = _next_power_of_two(n)
    h     = n_pad.bit_length() - 1
    med, lo, hi = bench_proof(n, repeat=500)
    print(f"    {n:>6}  {h:>8}  {h:>16}  {med:>9.3f}µs  {lo:>6.3f}µs")

# 6. Vérification de preuve
print(f"\n[6] Verification de preuve verify_proof(leaf, proof, root)")
print(f"    {'n':>6}  {'appels_sha256':>14}  {'mediane':>10}  {'min':>8}")
for n in [10, 50, 100, 300, 1000, 5000]:
    n_pad = _next_power_of_two(n)
    h     = n_pad.bit_length() - 1
    med, lo, hi = bench_verify(n, repeat=500)
    print(f"    {n:>6}  {h:>14}  {med:>9.3f}µs  {lo:>6.3f}µs")

# 7. Coût total d'une insertion simulée (reconstruct arbre complet)
print(f"\n[7] Cout total insertion (hachage de toutes les feuilles + build_tree)")
print(f"    {'n':>6}  {'mediane_ms':>12}  {'min_ms':>8}")
for n in [10, 50, 100, 300, 500, 1000, 5000]:
    diplomes = [make_diplome(i) for i in range(n)]
    def full_insert():
        hashes = [compute_hash(d) for d in diplomes]
        build_tree(hashes)
    rep = max(20, 200 // (n // 50 + 1))
    med, lo, hi = bench(full_insert, repeat=rep)
    print(f"    {n:>6}  {med/1000:>11.3f}ms  {lo/1000:>6.3f}ms")

# 8. Taille des preuves
print(f"\n[8] Taille des preuves (nombre de hashs dans le chemin)")
for n in [10, 50, 100, 300, 1000, 5000]:
    hashes = [compute_hash(make_diplome(i)) for i in range(n)]
    tree   = build_tree(hashes)
    proof  = generate_proof(tree, n // 2)
    # Taille JSON approximative
    import json
    proof_json = json.dumps({
        'leafHash':  hashes[n // 2],
        'leafIndex': n // 2,
        'treeSize':  _next_power_of_two(n),
        'root':      get_root(tree),
        'annee':     2024,
        'path':      [{'siblingHash': s['sibling_hash'], 'direction': s['direction']} for s in proof],
    })
    print(f"    n={n:>5} : {len(proof)} elements dans le chemin, taille JSON = {len(proof_json)} octets ({len(proof_json)//1024 if len(proof_json)>1024 else len(proof_json)} {'Ko' if len(proof_json)>1024 else 'octets'})")

print("\n" + "=" * 70)
print("Benchmark termine.")
print("=" * 70)
