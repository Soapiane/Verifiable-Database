import hashlib
from django.db import models


MENTIONS = [
    ('passable',    'Passable'),
    ('assez_bien',  'Assez Bien'),
    ('bien',        'Bien'),
    ('tres_bien',   'Très Bien'),
    ('felicitations', 'Félicitations du jury'),
]


class Diplome(models.Model):
    numero_etudiant  = models.CharField(max_length=20, unique=True)
    nom              = models.CharField(max_length=100)
    prenom           = models.CharField(max_length=100)
    intitule         = models.CharField(max_length=200)   # ex: Master Informatique
    specialite       = models.CharField(max_length=200)   # ex: Cybersécurité
    universite       = models.CharField(max_length=200)
    faculte          = models.CharField(max_length=200)
    date_obtention   = models.DateField()
    mention          = models.CharField(max_length=20, choices=MENTIONS)
    created_at       = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        """Format canonique partagé avec merkle.js — NE PAS MODIFIER sans mettre à jour le JS."""
        return '|'.join([
            str(self.id),
            self.numero_etudiant,
            self.nom,
            self.prenom,
            self.intitule,
            self.specialite,
            self.universite,
            self.faculte,
            str(self.date_obtention),   # YYYY-MM-DD
            self.mention,
        ])

    def compute_hash(self):
        return hashlib.sha256(self.serialize().encode('utf-8')).hexdigest()

    def get_mention_display_fr(self):
        return dict(MENTIONS).get(self.mention, self.mention)

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.intitule}"

    class Meta:
        ordering = ['-date_obtention']


class MerkleLeaf(models.Model):
    diplome    = models.OneToOneField(Diplome, on_delete=models.CASCADE, related_name='merkle_leaf')
    leaf_index = models.IntegerField(unique=True)
    leaf_hash  = models.CharField(max_length=64)

    def __str__(self):
        return f"Leaf[{self.leaf_index}] → {self.diplome}"


class RootHistory(models.Model):
    root_hash  = models.CharField(max_length=64)
    tree_size  = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Root {self.root_hash[:12]}... (size={self.tree_size})"


class AnnualRoot(models.Model):
    """Racine Merkle officielle publiée chaque année — une entrée par promotion."""
    annee          = models.IntegerField(unique=True)
    root_hash      = models.CharField(max_length=64)
    diploma_count  = models.IntegerField()
    published_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-annee']

    def __str__(self):
        return f"Promotion {self.annee} — Root {self.root_hash[:12]}..."
