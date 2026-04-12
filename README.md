# DiploVerif — Registre National des Diplomes Verifiables

Un backend Django pour emettre et verifier des diplomes academiques a l'aide d'**arbres de Merkle SHA-256**. Chaque diplome est hache et insere comme feuille dans un arbre de Merkle. La racine sert d'empreinte compacte et infalsifiable de l'ensemble du registre.

---

## Setup

### Prerequis

- Python 3.11+
- pip

### 1. Creer et activer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Installer les dependances

```bash
pip install -r requirements.txt
```

### 3. Appliquer les migrations

```bash
python manage.py migrate
```

### 4. (Optionnel) Peupler la base avec des donnees de test

```bash
python seed.py
```

---

## Usage

### Lancer le serveur de developpement

```bash
python manage.py runserver
```

L'application est disponible sur http://127.0.0.1:8000/

### Essayer l'application

> **Note :** La page **Registre** (`/registre/`) n'est pas destinee a etre publique. C'est un playground qui permet de consulter l'ensemble des diplomes et d'en soumettre de nouveaux facilement pour tester.

#### Scenario 1 — Verifier un diplome authentique

1. Aller sur `/registre/` et cliquer sur **Verifier** a cote d'un diplome (ou aller directement sur `/diplomes/1/`)
2. Sur la page du diplome, cliquer sur **Verifier contre la racine nationale**
3. Le calcul s'execute entierement dans le navigateur (WebCrypto API). Le resultat doit etre **DIPLOME AUTHENTIQUE** : le hash recalcule localement correspond a la racine Merkle certifiee
4. L'arbre Merkle s'anime en vert pour montrer le chemin de preuve valide

#### Scenario 2 — Detecter une falsification

1. Ouvrir un diplome (ex: `/diplomes/1/`)
2. En bas a gauche, dans le panneau **Simulation de falsification**, modifier un champ (ex: changer la mention de "Tres Bien" a "Felicitations du jury", ou modifier l'intitule du diplome)
3. Cliquer sur **Appliquer la falsification locale** — le diplome affiche se met a jour avec les nouvelles valeurs
4. Cliquer sur **Verifier contre la racine nationale**
5. Le resultat est **FALSIFICATION DETECTEE** : le hash recalcule a partir des donnees modifiees ne correspond plus a la racine publiee. L'arbre s'anime en rouge
6. Cette detection fonctionne sans aucun appel serveur — la preuve et la racine se suffisent a elles-memes

### Pages

| URL | Description |
|-----|-------------|
| `/` | Archives annuelles — arbre de Merkle par promotion |
| `/registre/` | Playground — registre complet, soumission de diplomes |
| `/diplomes/<id>/` | Detail d'un diplome avec verification et simulation de falsification |

### API

| Methode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/diplomes/` | Enregistrer un nouveau diplome |
| `GET` | `/api/root/` | Racine Merkle actuelle et taille de l'arbre |
| `GET` | `/api/roots/export/` | Telecharger toutes les racines annuelles (JSON) |
| `POST` | `/api/diplomes/<id>/tamper/` | Demo — falsifier un diplome sans mettre a jour l'arbre |

**Valeurs de mention :** `passable` | `assez_bien` | `bien` | `tres_bien` | `felicitations`

---

## Tests

Lancer la suite de tests :

```bash
python manage.py test diplomes
```

Avec le detail par test :

```bash
python manage.py test diplomes -v 2
```

Les tests couvrent :
- **Merkle** — construction d'arbre, padding, generation et verification de preuves, detection de falsification
- **Modeles** — serialisation canonique, determinisme du hash
- **Arbres annuels** — filtrage par promotion, stockage des racines, round-trip preuve complet
- **API** — creation de diplome, champs manquants, doublons, falsification, export

---

## Fonctionnement

1. Chaque diplome est serialise en chaine canonique : `id|numero_etudiant|nom|prenom|intitule|specialite|universite|faculte|date_obtention|mention`
2. Cette chaine est hachee avec SHA-256 pour produire un **hash de feuille**.
3. Tous les hashs de feuilles forment un **arbre de Merkle** (complete a la puissance de 2 superieure avec `SHA256(EMPTY)`).
4. La **racine** engage l'ensemble du registre. Toute modification d'un diplome produit une racine differente.
5. Pour chaque diplome, une **preuve Merkle** (chemin de la feuille a la racine) peut etre generee et verifiee independamment.

---

## Structure du projet

```
.
├── manage.py
├── requirements.txt
├── seed.py                      # Chargement de donnees de test
├── diploverif/                  # Configuration du projet Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── diplomes/                    # Application principale
    ├── models.py                # Diplome, MerkleLeaf, RootHistory, AnnualRoot
    ├── merkle.py                # Moteur Merkle (Python pur)
    ├── urls.py                  # Routage des URLs
    ├── tests.py                 # Suite de tests (37 tests)
    ├── views/
    │   ├── pages.py             # Pages HTML (dashboard, detail, archives)
    │   ├── api.py               # Endpoints JSON (create, tamper, root, export)
    │   └── helpers.py           # Logique partagee (parsing, preuves, stats)
    └── templates/diplomes/
        ├── base.html
        ├── dashboard.html
        ├── diplome_detail.html
        └── archives.html
```
