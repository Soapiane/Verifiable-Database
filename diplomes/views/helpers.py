import json

from django.db.models import Count
from django.http import JsonResponse

from ..models import Diplome, AnnualRoot
from .. import merkle


def parse_json_body(request):
    """Parse le body JSON. Retourne (data, None) ou (None, JsonResponse d'erreur)."""
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'JSON invalide'}, status=400)


def build_proof_context(diplome):
    """Construit l'arbre annuel et la preuve Merkle pour un diplôme donné."""
    annee = diplome.date_obtention.year
    tree, diplomes_annee, _ = merkle.build_annual_tree(annee)
    leaf_index = next(i for i, d in enumerate(diplomes_annee) if d.id == diplome.id)
    proof_steps = merkle.generate_proof(tree, leaf_index)

    annual_root = AnnualRoot.objects.filter(annee=annee).first()
    root_hash = annual_root.root_hash if annual_root else merkle.get_root(tree)

    return {
        'leaf_index':  leaf_index,
        'leaf_hash':   diplome.compute_hash(),
        'root_hash':   root_hash,
        'annee':       annee,
        'proof_steps': proof_steps,
        'tree_json':   merkle.tree_to_json(tree, proof_leaf_index=leaf_index),
        'tree_size':   len(diplomes_annee),
    }


def compute_promotion_stats(annee, diploma_count):
    """Calcule les statistiques d'une promotion (mentions, universités, intitulés)."""
    base_qs = Diplome.objects.filter(date_obtention__year=annee)

    mentions_qs = base_qs.values('mention').annotate(nb=Count('id'))
    mentions = {m['mention']: m['nb'] for m in mentions_qs}

    nb_honneur = (mentions.get('bien', 0)
                  + mentions.get('tres_bien', 0)
                  + mentions.get('felicitations', 0))

    return {
        'nb_universites': base_qs.values('universite').distinct().count(),
        'nb_intitules':   base_qs.values('intitule').distinct().count(),
        'nb_honneur':     nb_honneur,
        'pct_honneur':    round(nb_honneur * 100 / diploma_count) if diploma_count else 0,
        'mentions':       mentions,
    }
