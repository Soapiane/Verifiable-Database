# DiploVerif — Registre National des Diplomes Verifiables

Un backend Django pour emettre et verifier des diplomes academiques a l'aide d'**arbres de Merkle SHA-256**. Chaque diplome est hache et insere comme feuille dans un arbre de Merkle. La racine sert d'empreinte compacte et infalsifiable de l'ensemble du registre.

---

## Installation

### Prerequis

- Python 3.11+
- pip

### 1. Creer et activer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scriptsctivate

# macOS / Linux
source venv/bin/activate
```

### 3. Installer les dependances

```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations

```bash
python manage.py migrate
```

### 5. (Optionnel) Peupler la base avec des donnees de test

```bash
python seed.py
```

### 6. Lancer le serveur de developpement

```bash
python manage.py runserver
```

L'application est disponible sur http://127.0.0.1:8000/

---

## Utilisation

### Pages

| URL | Description |
|-----|-------------|
| `/` | Archives annuelles — arbre de Merkle par promotion |
| `/registre/` | Tableau de bord — registre complet des diplomes |
| `/diplomes/<id>/` | Detail d'un diplome avec visualisation de la preuve Merkle |

### Endpoints API

| Methode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/root/` | Racine Merkle actuelle et taille de l'arbre |
| `POST` | `/api/diplomes/` | Enregistrer un nouveau diplome |
| `GET` | `/api/roots/export/` | Telecharger toutes les racines annuelles en JSON |
| `POST` | `/api/diplomes/<id>/tamper/` | Demo uniquement — falsifier un diplome sans mettre a jour l'arbre |

### Enregistrer un diplome (POST /api/diplomes/)

**Valeurs de mention :** passable | assez_bien | bien | tres_bien | felicitations

### Obtenir la racine actuelle (GET /api/root/)

### Exporter les racines annuelles (GET /api/roots/export/)

Retourne un fichier JSON contenant toutes les racines Merkle annuelles certifiees, adapte a l'archivage public ou a l'ancrage blockchain.

---

## Fonctionnement

1. Chaque diplome est serialise en chaine canonique : id|numero_etudiant|nom|prenom|intitule|specialite|universite|faculte|date_obtention|mention
2. Cette chaine est hachee avec SHA-256 pour produire un **hash de feuille**.
3. Tous les hashs de feuilles forment un **arbre de Merkle** (complete a la puissance de 2 superieure avec SHA256(EMPTY)).
4. La **racine** engage l'ensemble du registre. Toute modification d'un diplome produit une racine differente.
5. Pour chaque diplome, une **preuve Merkle** (chemin de la feuille a la racine) peut etre generee et verifiee independamment.

---

## Structure du projet

```
.
├── manage.py
├── requirements.txt
├── seed.py                  # Chargement de donnees de test
├── pharmleder/              # Configuration du projet Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── lots/                    # Application principale
    ├── models.py            # Diplome, MerkleLeaf, RootHistory, AnnualRoot
    ├── views.py             # Pages HTML + API JSON
    ├── urls.py              # Routage des URLs
    ├── merkle.py            # Moteur Merkle (Python pur)
    └── migrations/
```
