from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from ..models import Diplome, RootHistory, AnnualRoot
from .. import merkle
from .helpers import parse_json_body


@csrf_exempt
@require_POST
def create_diplome(request):
    data, error = parse_json_body(request)
    if error:
        return error

    required = ['numero_etudiant', 'nom', 'prenom', 'intitule', 'specialite',
                'universite', 'faculte', 'date_obtention', 'mention']
    for field in required:
        if field not in data:
            return JsonResponse({'error': f'Champ manquant : {field}'}, status=400)

    if Diplome.objects.filter(numero_etudiant=data['numero_etudiant']).exists():
        return JsonResponse({'error': 'Numéro étudiant déjà enregistré'}, status=409)

    diplome = Diplome.objects.create(**{k: data[k] for k in required})
    diplome.refresh_from_db()  # force la conversion date string → DateField

    annee       = diplome.date_obtention.year
    annual_root = merkle.compute_and_store_annual_root(annee)

    return JsonResponse({'id': diplome.id, 'root': annual_root}, status=201)


@csrf_exempt
@require_POST
def tamper_diplome(request, diplome_id):
    """Route de démonstration : falsifie un dipl��me sans mettre à jour le Merkle tree."""
    diplome = get_object_or_404(Diplome, id=diplome_id)
    data, error = parse_json_body(request)
    if error:
        return error

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
