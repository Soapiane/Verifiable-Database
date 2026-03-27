import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmleder.settings')
django.setup()

from lots.models import Diplome, MerkleLeaf, RootHistory, AnnualRoot
from lots import merkle

DIPLOMES = [
    # ── Promotion 2022 ────────────────────────────────────────────────────────
    ("ETU-2022-001", "Rousseau",  "Clara",    "Licence Informatique",          "Systemes et Reseaux",              "Universite Paris-Saclay",          "Faculte des Sciences",              "2022-07-04", "bien"),
    ("ETU-2022-002", "Fontaine",  "Hugo",     "Master Droit",                  "Droit public",                     "Universite Paris 1 Pantheon",      "Faculte de Droit",                  "2022-07-08", "assez_bien"),
    ("ETU-2022-003", "Garnier",   "Lea",      "Licence Biologie",              "Genetique moleculaire",            "Universite Claude Bernard Lyon 1", "UFR Sciences du Vivant",            "2022-07-01", "tres_bien"),
    ("ETU-2022-004", "Chevalier", "Maxime",   "Master Finance",                "Finance de marche",                "HEC Paris",                        "Departement Finance",               "2022-07-06", "felicitations"),

    # ── Promotion 2023 ────────────────────────────────────────────────────────
    ("ETU-2023-001", "Morin",     "Pauline",  "Master Informatique",           "Intelligence Artificielle",        "Ecole Polytechnique",              "Departement Informatique",          "2023-07-05", "tres_bien"),
    ("ETU-2023-002", "Girard",    "Theo",     "Licence Economie",              "Economie internationale",          "Sciences Po Paris",                "Departement Economie",              "2023-07-10", "bien"),
    ("ETU-2023-003", "Bonnet",    "Emilie",   "Master Medecine",               "Neurologie",                       "Universite de Montpellier",        "Faculte de Medecine",               "2023-07-03", "felicitations"),
    ("ETU-2023-004", "Perrin",    "Romain",   "Doctorat Physique",             "Physique des particules",          "Universite Paris-Saclay",          "Faculte des Sciences",              "2023-06-20", "felicitations"),
    ("ETU-2023-005", "Clement",   "Oceane",   "Licence Psychologie",           "Psychologie clinique",             "Universite Paris 8",               "UFR Psychologie",                   "2023-07-07", "assez_bien"),

    # ── Promotion 2024 ────────────────────────────────────────────────────────
    ("ETU-2024-001", "Dupont",    "Marie",    "Master Informatique",           "Cybersecurite et Bases de Donnees","Universite Paris-Saclay",          "Faculte des Sciences",              "2024-07-02", "tres_bien"),
    ("ETU-2024-002", "Moreau",    "Thomas",   "Licence Droit",                 "Droit des affaires",               "Universite Paris 1 Pantheon",      "Faculte de Droit",                  "2024-07-05", "bien"),
    ("ETU-2024-003", "Lefevre",   "Sophie",   "Master Medecine",               "Cardiologie",                      "Universite de Montpellier",        "Faculte de Medecine",               "2024-06-28", "felicitations"),
    ("ETU-2024-004", "Bernard",   "Lucas",    "Licence Economie",              "Economie internationale",          "Sciences Po Paris",                "Departement Economie",              "2024-07-10", "assez_bien"),
    ("ETU-2024-005", "Petit",     "Camille",  "Master Data Science",           "Intelligence Artificielle",        "Ecole Polytechnique",              "Departement Informatique",          "2024-07-03", "tres_bien"),
    ("ETU-2024-006", "Laurent",   "Antoine",  "Licence Physique",              "Physique theorique",               "Universite Claude Bernard Lyon 1", "UFR de Physique",                   "2024-07-08", "bien"),
    ("ETU-2024-007", "Simon",     "Juliette", "Master Gestion",                "Finance d entreprise",             "HEC Paris",                        "Departement Finance",               "2024-07-01", "tres_bien"),
    ("ETU-2024-008", "Michel",    "Nathan",   "Doctorat Informatique",         "Cryptographie appliquee",          "Universite Paris-Saclay",          "Faculte des Sciences",              "2024-06-15", "felicitations"),
]

# Nettoyage
AnnualRoot.objects.all().delete()
RootHistory.objects.all().delete()
MerkleLeaf.objects.all().delete()
Diplome.objects.all().delete()

# Insertion
for i, (num, nom, prenom, intitule, specialite, universite, faculte, date, mention) in enumerate(DIPLOMES):
    d = Diplome.objects.create(
        numero_etudiant=num, nom=nom, prenom=prenom,
        intitule=intitule, specialite=specialite,
        universite=universite, faculte=faculte,
        date_obtention=date, mention=mention,
    )
    MerkleLeaf.objects.create(diplome=d, leaf_index=i, leaf_hash=d.compute_hash())
    print(f"OK {num} - {prenom} {nom} ({date[:4]})")

# Racine globale
tree, _ = merkle.rebuild_tree_from_db()
global_root = merkle.get_root(tree)
RootHistory.objects.create(root_hash=global_root, tree_size=len(DIPLOMES))

# Racines annuelles
for annee in [2022, 2023, 2024]:
    root = merkle.compute_and_store_annual_root(annee)
    count = Diplome.objects.filter(date_obtention__year=annee).count()
    print(f"Promotion {annee} : {count} diplomes — root={root[:16]}...")

print(f"\nDONE: {len(DIPLOMES)} diplomes sur 3 promotions")
print(f"Root global : {global_root}")
