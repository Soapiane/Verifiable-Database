import json

from django.db.models import Count
from django.shortcuts import render, get_object_or_404

from ..models import Diplome, AnnualRoot
from .. import merkle
from .helpers import build_proof_context, compute_promotion_stats


def dashboard(request):
    diplomes     = Diplome.objects.all()
    annual_roots = AnnualRoot.objects.all()
    universites  = (Diplome.objects
                    .values('universite')
                    .annotate(nb=Count('id'))
                    .order_by('universite'))
    return render(request, 'diplomes/dashboard.html', {
        'diplomes':     diplomes,
        'annual_roots': annual_roots,
        'universites':  universites,
    })


def diplome_detail(request, diplome_id):
    diplome = get_object_or_404(Diplome, id=diplome_id)
    ctx = build_proof_context(diplome)

    proof_data = {
        'leafHash':  ctx['leaf_hash'],
        'leafIndex': ctx['leaf_index'],
        'treeSize':  ctx['tree_size'],
        'root':      ctx['root_hash'],
        'annee':     ctx['annee'],
        'path': [
            {'siblingHash': s['sibling_hash'], 'direction': s['direction']}
            for s in ctx['proof_steps']
        ],
    }

    return render(request, 'diplomes/diplome_detail.html', {
        'diplome':            diplome,
        'root':               ctx['root_hash'],
        'annee':              ctx['annee'],
        'annual_leaf_index':  ctx['leaf_index'],
        'leaf_hash':          ctx['leaf_hash'],
        'diplome_json':       json.dumps(diplome.to_api_dict()),
        'proof_json':         json.dumps(proof_data),
        'tree_json':          json.dumps(ctx['tree_json']),
    })


def archives(request):
    """Page affichant l'arbre Merkle et les statistiques de chaque promotion."""
    annual_roots = AnnualRoot.objects.all()

    years_data = []
    for ar in annual_roots:
        tree, diplomes, _ = merkle.build_annual_tree(ar.annee)
        years_data.append({
            'annee':         ar.annee,
            'root_hash':     ar.root_hash,
            'diploma_count': ar.diploma_count,
            'published_at':  ar.published_at,
            'tree_json':     json.dumps(merkle.tree_to_json(tree)),
            'stats':         compute_promotion_stats(ar.annee, ar.diploma_count),
        })

    return render(request, 'diplomes/archives.html', {'years_data': years_data})
