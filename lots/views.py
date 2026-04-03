import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import Diplome, RootHistory, AnnualRoot
from . import merkle


def dashboard(request):
    from django.db.models import Count
    diplomes     = Diplome.objects.all()
    annual_roots = AnnualRoot.objects.all()
    universites  = (Diplome.objects
                    .values('universite')
                    .annotate(nb=Count('id'))
                    .order_by('universite'))
    return render(request, 'lots/dashboard.html', {
        'diplomes':     diplomes,
        'annual_roots': annual_roots,
        'universites':  universites,
    })


def diplome_detail(request, diplome_id):
    diplome = get_object_or_404(Diplome, id=diplome_id)
    annee   = diplome.date_obtention.year

    # Arbre uniquement pour la promotion de ce diplôme
    tree, diplomes_annee, _ = merkle.build_annual_tree(annee)
    annual_leaf_index = next(i for i, d in enumerate(diplomes_annee) if d.id == diplome.id)
    leaf_hash   = diplome.compute_hash()
    proof_steps = merkle.generate_proof(tree, annual_leaf_index)
    tree_json   = merkle.tree_to_json(tree, proof_leaf_index=annual_leaf_index)

    annual_root = AnnualRoot.objects.filter(annee=annee).first()
    root_hash   = annual_root.root_hash if annual_root else merkle.get_root(tree)

    diplome_data = {
        'id':             diplome.id,
        'numeroEtudiant': diplome.numero_etudiant,
        'nom':            diplome.nom,
        'prenom':         diplome.prenom,
        'intitule':       diplome.intitule,
        'specialite':     diplome.specialite,
        'universite':     diplome.universite,
        'faculte':        diplome.faculte,
        'dateObtention':  str(diplome.date_obtention),
        'mention':        diplome.mention,
    }

    proof_data = {
        'leafHash':  leaf_hash,
        'leafIndex': annual_leaf_index,
        'treeSize':  len(diplomes_annee),
        'root':      root_hash,
        'annee':     annee,
        'path': [
            {'siblingHash': s['sibling_hash'], 'direction': s['direction']}
            for s in proof_steps
        ],
    }

    return render(request, 'lots/diplome_detail.html', {
        'diplome':            diplome,
        'root':               root_hash,
        'annee':              annee,
        'annual_leaf_index':  annual_leaf_index,
        'leaf_hash':          leaf_hash,
        'diplome_json':       json.dumps(diplome_data),
        'proof_json':         json.dumps(proof_data),
        'tree_json':          json.dumps(tree_json),
    })


@csrf_exempt
@require_POST
def create_diplome(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    required = ['numero_etudiant', 'nom', 'prenom', 'intitule', 'specialite',
                'universite', 'faculte', 'date_obtention', 'mention']
    for field in required:
        if field not in data:
            return JsonResponse({'error': f'Champ manquant : {field}'}, status=400)

    if Diplome.objects.filter(numero_etudiant=data['numero_etudiant']).exists():
        return JsonResponse({'error': 'Numéro étudiant déjà enregistré'}, status=409)

    diplome = Diplome.objects.create(**{k: data[k] for k in required})

    # Racine annuelle uniquement. Les preuves sont valides pour toujours.
    annee       = diplome.date_obtention.year
    annual_root = merkle.compute_and_store_annual_root(annee)

    return JsonResponse({'id': diplome.id, 'root': annual_root}, status=201)


@csrf_exempt
@require_POST
def tamper_diplome(request, diplome_id):
    """Route de démonstration : falsifie un diplôme sans mettre à jour le Merkle tree."""
    diplome = get_object_or_404(Diplome, id=diplome_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    allowed = {'mention', 'intitule', 'specialite'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return JsonResponse({'error': 'Aucun champ modifiable fourni'}, status=400)

    Diplome.objects.filter(id=diplome_id).update(**updates)
    return JsonResponse({
        'warning': 'Diplôme modifié HORS Merkle tree. La preuve est désormais invalide.',
        'changes': updates,
    })


@require_GET
def api_root(request):
    root = RootHistory.objects.first()
    if not root:
        return JsonResponse({'root': None, 'tree_size': 0})
    return JsonResponse({'root': root.root_hash, 'tree_size': root.tree_size})


def archives(request):
    """Page affichant l'arbre Merkle et les statistiques de chaque promotion."""
    from django.db.models import Count
    annual_roots = AnnualRoot.objects.all()

    years_data = []
    for ar in annual_roots:
        tree, diplomes, _ = merkle.build_annual_tree(ar.annee)

        # Statistiques des mentions
        mentions_qs = (Diplome.objects
                       .filter(date_obtention__year=ar.annee)
                       .values('mention')
                       .annotate(nb=Count('id')))
        mentions = {m['mention']: m['nb'] for m in mentions_qs}

        nb_honneur = (mentions.get('bien', 0)
                      + mentions.get('tres_bien', 0)
                      + mentions.get('felicitations', 0))
        pct_honneur = round(nb_honneur * 100 / ar.diploma_count) if ar.diploma_count else 0

        # Universités distinctes
        nb_universites = (Diplome.objects
                          .filter(date_obtention__year=ar.annee)
                          .values('universite').distinct().count())

        # Intitulés distincts
        nb_intitules = (Diplome.objects
                        .filter(date_obtention__year=ar.annee)
                        .values('intitule').distinct().count())

        years_data.append({
            'annee':         ar.annee,
            'root_hash':     ar.root_hash,
            'diploma_count': ar.diploma_count,
            'published_at':  ar.published_at,
            'tree_json':     json.dumps(merkle.tree_to_json(tree)),
            'stats': {
                'nb_universites': nb_universites,
                'nb_intitules':   nb_intitules,
                'pct_honneur':    pct_honneur,
                'nb_honneur':     nb_honneur,
                'mentions':       mentions,
            },
        })

    return render(request, 'lots/archives.html', {'years_data': years_data})


@require_GET
def export_roots(request):
    """Téléchargement JSON de toutes les racines annuelles."""
    annual_roots = AnnualRoot.objects.all()
    data = {
        'registry':    'DiploVerif, Registre National des Diplômes',
        'description': 'Racines Merkle annuelles certifiées. Chaque racine engage l\'ensemble des diplômes de la promotion correspondante.',
        'algorithm':   'SHA-256 Merkle Tree',
        'roots': [
            {
                'annee':         ar.annee,
                'root_hash':     ar.root_hash,
                'diploma_count': ar.diploma_count,
                'published_at':  ar.published_at.isoformat(),
            }
            for ar in annual_roots
        ],
    }
    response = JsonResponse(data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    response['Content-Disposition'] = 'attachment; filename="diploVerif_roots.json"'
    return response
