import hashlib

# ---------------------------------------------------------------------------
# Moteur Merkle
# ---------------------------------------------------------------------------

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
            'sibling_hash': level[sibling_index],
            'direction':    'right' if is_left_node else 'left',
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


# ---------------------------------------------------------------------------
# Modele de diplome (standalone, sans Django)
# ---------------------------------------------------------------------------

class Diplome:
    _next_id = 1

    def __init__(self, numero_etudiant, nom, prenom, intitule,
                 specialite, universite, faculte, date_obtention, mention):
        self.id               = Diplome._next_id
        Diplome._next_id     += 1
        self.numero_etudiant  = numero_etudiant
        self.nom              = nom
        self.prenom           = prenom
        self.intitule         = intitule
        self.specialite       = specialite
        self.universite       = universite
        self.faculte          = faculte
        self.date_obtention   = date_obtention
        self.mention          = mention

    def serialize(self):
        """Format canonique identique a lots/models.py."""
        return '|'.join([
            str(self.id),
            self.numero_etudiant,
            self.nom,
            self.prenom,
            self.intitule,
            self.specialite,
            self.universite,
            self.faculte,
            self.date_obtention,
            self.mention,
        ])

    def compute_hash(self):
        return sha256(self.serialize())

    def __str__(self):
        return f"{self.prenom} {self.nom}, {self.intitule} ({self.date_obtention[:4]})"


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

SEP  = "=" * 60
SEP2 = "-" * 60

def titre(texte):
    print(f"\n{SEP}\n  {texte}\n{SEP}")

def ok(texte):
    print(f"  [OK]  {texte}")

def err(texte):
    print(f"  [!!]  {texte}")

def info(texte):
    print(f"        {texte}")


# ---------------------------------------------------------------------------
# SCENARIO 1 : Enregistrement et construction de l'arbre
# ---------------------------------------------------------------------------

titre("SCENARIO 1 : Enregistrement des diplomes")

diplomes = [
    Diplome("ETU-2024-001", "Dupont",  "Marie",   "Master Informatique",  "Cybersecurite",             "Universite Paris-Saclay",  "Faculte des Sciences", "2024-07-02", "tres_bien"),
    Diplome("ETU-2024-002", "Moreau",  "Thomas",  "Licence Droit",        "Droit des affaires",        "Universite Paris 1",       "Faculte de Droit",     "2024-07-05", "bien"),
    Diplome("ETU-2024-003", "Lefevre", "Sophie",  "Master Medecine",      "Cardiologie",               "Univ. de Montpellier",     "Faculte de Medecine",  "2024-06-28", "felicitations"),
    Diplome("ETU-2024-004", "Bernard", "Lucas",   "Licence Economie",     "Economie internationale",   "Sciences Po Paris",        "Dept. Economie",       "2024-07-10", "assez_bien"),
    Diplome("ETU-2024-005", "Petit",   "Camille", "Master Data Science",  "Intelligence Artificielle", "Ecole Polytechnique",      "Dept. Informatique",   "2024-07-03", "tres_bien"),
]

leaf_hashes = []
for d in diplomes:
    h = d.compute_hash()
    leaf_hashes.append(h)
    ok(f"{d}  =>  hash={h[:16]}...")

tree = build_tree(leaf_hashes)
root = get_root(tree)

print(f"\n  Arbre construit : {len(diplomes)} diplomes, {len(tree)} niveaux")
print(f"  Racine Merkle   : {root}")


# ---------------------------------------------------------------------------
# SCENARIO 2 : Verification d'un diplome legitime
# ---------------------------------------------------------------------------

titre("SCENARIO 2 : Verification d'un diplome legitime")

cible       = diplomes[2]   # Sophie Lefevre
cible_index = 2
cible_hash  = leaf_hashes[cible_index]
proof       = generate_proof(tree, cible_index)
valide      = verify_proof(cible_hash, proof, root)

info(f"Diplome  : {cible}")
info(f"Hash     : {cible_hash[:16]}...")
info(f"Preuve   : {len(proof)} etape(s)")
for i, step in enumerate(proof):
    info(f"  etape {i+1} : sibling={step['sibling_hash'][:12]}... direction={step['direction']}")

print()
if valide:
    ok("Preuve VALIDE : le diplome est authentique et non modifie.")
else:
    err("Preuve INVALIDE.")


# ---------------------------------------------------------------------------
# SCENARIO 3 : Detection d'une falsification
# ---------------------------------------------------------------------------

titre("SCENARIO 3 : Falsification et detection")

info(f"Diplome original : mention='{cible.mention}'")
info("Falsification    : on change la mention en 'felicitations' sans recomputer l'arbre...")

cible_falsifie        = Diplome.__new__(Diplome)
cible_falsifie.__dict__ = dict(cible.__dict__)
cible_falsifie.mention  = "felicitations" if cible.mention != "felicitations" else "passable"

hash_falsifie  = cible_falsifie.compute_hash()
valide_falsif  = verify_proof(hash_falsifie, proof, root)

info(f"Hash falsifie    : {hash_falsifie[:16]}...")
print()
if not valide_falsif:
    ok("Falsification DETECTEE : la preuve Merkle est invalide pour le diplome modifie.")
else:
    err("Falsification non detectee (anomalie).")


# ---------------------------------------------------------------------------
# SCENARIO 4 : Ajout d'un nouveau diplome
# ---------------------------------------------------------------------------

titre("SCENARIO 4 : Ajout d'un nouveau diplome et mise a jour de la racine")

ancien_root = root

nouveau = Diplome("ETU-2024-006", "Laurent", "Antoine", "Licence Physique",
                  "Physique theorique", "Univ. Claude Bernard Lyon 1",
                  "UFR de Physique", "2024-07-08", "bien")

diplomes.append(nouveau)
leaf_hashes.append(nouveau.compute_hash())

tree_v2   = build_tree(leaf_hashes)
root_v2   = get_root(tree_v2)

info(f"Nouveau diplome  : {nouveau}")
info(f"Ancienne racine  : {ancien_root[:16]}...")
info(f"Nouvelle racine  : {root_v2[:16]}...")
print()
if root_v2 != ancien_root:
    ok("Racine mise a jour : l'ajout est bien reflete dans l'arbre.")

# Verification que l'ancien diplome est toujours valide avec la nouvelle racine
proof_v2 = generate_proof(tree_v2, cible_index)
valide_v2 = verify_proof(leaf_hashes[cible_index], proof_v2, root_v2)
if valide_v2:
    ok(f"Le diplome de {cible.prenom} {cible.nom} reste valide dans le nouvel arbre.")

print(f"\n{SEP}")
print(f"  FIN DU POC : {len(diplomes)} diplomes enregistres")
print(f"  Racine finale : {root_v2}")
print(SEP)
