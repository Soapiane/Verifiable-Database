import json
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse

from .models import Diplome, AnnualRoot, RootHistory, MENTIONS
from . import merkle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diplome(**overrides):
    """Crée un diplôme en base avec des valeurs par défaut."""
    defaults = {
        'numero_etudiant': 'ETU-TEST-001',
        'nom':             'Dupont',
        'prenom':          'Marie',
        'intitule':        'Master Informatique',
        'specialite':      'Cybersécurité',
        'universite':      'Université Paris-Saclay',
        'faculte':         'Faculté des Sciences',
        'date_obtention':  date(2024, 7, 2),
        'mention':         'tres_bien',
    }
    defaults.update(overrides)
    return Diplome.objects.create(**defaults)


# ===========================================================================
# Tests merkle.py — fonctions pures
# ===========================================================================

class MerkleHashTest(TestCase):
    def test_sha256_deterministic(self):
        self.assertEqual(merkle.sha256('hello'), merkle.sha256('hello'))

    def test_sha256_differs_for_different_input(self):
        self.assertNotEqual(merkle.sha256('a'), merkle.sha256('b'))

    def test_hash_pair_order_matters(self):
        a, b = 'aaa', 'bbb'
        self.assertNotEqual(merkle.hash_pair(a, b), merkle.hash_pair(b, a))


class MerkleBuildTreeTest(TestCase):
    def test_empty_tree(self):
        tree = merkle.build_tree([])
        self.assertEqual(merkle.get_root(tree), merkle.EMPTY_HASH)

    def test_single_leaf(self):
        h = merkle.sha256('leaf0')
        tree = merkle.build_tree([h])
        # 1 feuille → _next_power_of_two(1) = 1, pas de padding, root = h itself
        self.assertEqual(len(tree[0]), 1)
        self.assertEqual(merkle.get_root(tree), h)

    def test_two_leaves(self):
        h0, h1 = merkle.sha256('a'), merkle.sha256('b')
        tree = merkle.build_tree([h0, h1])
        self.assertEqual(merkle.get_root(tree), merkle.hash_pair(h0, h1))

    def test_power_of_two_padding(self):
        """3 feuilles → paddé à 4, l'arbre a 3 niveaux."""
        hashes = [merkle.sha256(str(i)) for i in range(3)]
        tree = merkle.build_tree(hashes)
        self.assertEqual(len(tree[0]), 4)  # 4 feuilles (1 padding)
        self.assertEqual(len(tree), 3)     # 3 niveaux

    def test_four_leaves_no_padding(self):
        hashes = [merkle.sha256(str(i)) for i in range(4)]
        tree = merkle.build_tree(hashes)
        self.assertEqual(len(tree[0]), 4)
        self.assertEqual(len(tree), 3)


class MerkleProofTest(TestCase):
    def _build_and_verify(self, n_leaves):
        hashes = [merkle.sha256(f'leaf-{i}') for i in range(n_leaves)]
        tree = merkle.build_tree(hashes)
        root = merkle.get_root(tree)
        for idx in range(n_leaves):
            proof = merkle.generate_proof(tree, idx)
            self.assertTrue(
                merkle.verify_proof(hashes[idx], proof, root),
                f'Proof failed for leaf {idx} with {n_leaves} leaves',
            )

    def test_proof_1_leaf(self):
        self._build_and_verify(1)

    def test_proof_2_leaves(self):
        self._build_and_verify(2)

    def test_proof_3_leaves(self):
        self._build_and_verify(3)

    def test_proof_7_leaves(self):
        self._build_and_verify(7)

    def test_proof_8_leaves(self):
        self._build_and_verify(8)

    def test_wrong_leaf_fails(self):
        hashes = [merkle.sha256(f'leaf-{i}') for i in range(4)]
        tree = merkle.build_tree(hashes)
        root = merkle.get_root(tree)
        proof = merkle.generate_proof(tree, 0)
        fake_hash = merkle.sha256('TAMPERED')
        self.assertFalse(merkle.verify_proof(fake_hash, proof, root))

    def test_wrong_root_fails(self):
        hashes = [merkle.sha256(f'leaf-{i}') for i in range(4)]
        tree = merkle.build_tree(hashes)
        proof = merkle.generate_proof(tree, 0)
        self.assertFalse(merkle.verify_proof(hashes[0], proof, 'bad_root'))


class MerkleTreeToJsonTest(TestCase):
    def test_tree_to_json_structure(self):
        hashes = [merkle.sha256(str(i)) for i in range(4)]
        tree = merkle.build_tree(hashes)
        result = merkle.tree_to_json(tree)
        self.assertIn('nodes', result)
        self.assertIn('num_levels', result)
        self.assertIn('num_leaves', result)
        self.assertEqual(result['num_levels'], 3)
        self.assertEqual(result['num_leaves'], 4)

    def test_tree_to_json_proof_path_marked(self):
        hashes = [merkle.sha256(str(i)) for i in range(4)]
        tree = merkle.build_tree(hashes)
        result = merkle.tree_to_json(tree, proof_leaf_index=0)
        on_path = [n for n in result['nodes'] if n['on_path']]
        # Le chemin de preuve doit contenir un noeud par niveau
        self.assertEqual(len(on_path), result['num_levels'])


# ===========================================================================
# Tests models.py
# ===========================================================================

class DiplomeModelTest(TestCase):
    def test_serialize_format(self):
        d = _make_diplome()
        parts = d.serialize().split('|')
        self.assertEqual(len(parts), 10)
        self.assertEqual(parts[1], 'ETU-TEST-001')
        self.assertEqual(parts[2], 'Dupont')
        self.assertEqual(parts[8], '2024-07-02')
        self.assertEqual(parts[9], 'tres_bien')

    def test_compute_hash_deterministic(self):
        d = _make_diplome()
        self.assertEqual(d.compute_hash(), d.compute_hash())

    def test_compute_hash_changes_on_data_change(self):
        d = _make_diplome()
        h1 = d.compute_hash()
        d.mention = 'passable'
        h2 = d.compute_hash()
        self.assertNotEqual(h1, h2)

    def test_serialize_id_included(self):
        """Le hash dépend de l'id — un diplôme copié avec un id différent a un hash différent."""
        d = _make_diplome()
        parts = d.serialize().split('|')
        self.assertEqual(parts[0], str(d.id))


# ===========================================================================
# Tests annuels (merkle + DB)
# ===========================================================================

class AnnualTreeTest(TestCase):
    def setUp(self):
        self.d1 = _make_diplome(numero_etudiant='ETU-A-001', date_obtention=date(2024, 6, 1))
        self.d2 = _make_diplome(numero_etudiant='ETU-A-002', date_obtention=date(2024, 7, 1))
        self.d3 = _make_diplome(numero_etudiant='ETU-A-003', date_obtention=date(2023, 7, 1))

    def test_build_annual_tree_filters_by_year(self):
        tree, diplomes, hashes = merkle.build_annual_tree(2024)
        self.assertEqual(len(diplomes), 2)
        self.assertEqual(len(hashes), 2)

    def test_compute_and_store_annual_root(self):
        root = merkle.compute_and_store_annual_root(2024)
        ar = AnnualRoot.objects.get(annee=2024)
        self.assertEqual(ar.root_hash, root)
        self.assertEqual(ar.diploma_count, 2)

    def test_annual_root_updates_on_new_diplome(self):
        root1 = merkle.compute_and_store_annual_root(2024)
        _make_diplome(numero_etudiant='ETU-A-004', date_obtention=date(2024, 9, 1))
        root2 = merkle.compute_and_store_annual_root(2024)
        self.assertNotEqual(root1, root2)

    def test_proof_valid_for_annual_diplome(self):
        """Round-trip complet : construction arbre annuel → preuve → vérification."""
        merkle.compute_and_store_annual_root(2024)
        tree, diplomes, hashes = merkle.build_annual_tree(2024)
        root = merkle.get_root(tree)
        for idx, d in enumerate(diplomes):
            proof = merkle.generate_proof(tree, idx)
            self.assertTrue(merkle.verify_proof(d.compute_hash(), proof, root))


# ===========================================================================
# Tests API views
# ===========================================================================

class CreateDiplomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('create_diplome')
        self.valid_payload = {
            'numero_etudiant': 'ETU-VIEW-001',
            'nom':             'Martin',
            'prenom':          'Jean',
            'intitule':        'Licence Physique',
            'specialite':      'Optique',
            'universite':      'Université Lyon 1',
            'faculte':         'UFR Physique',
            'date_obtention':  '2024-07-01',
            'mention':         'bien',
        }

    def test_create_success(self):
        resp = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('id', data)
        self.assertIn('root', data)
        self.assertTrue(Diplome.objects.filter(numero_etudiant='ETU-VIEW-001').exists())

    def test_create_missing_field(self):
        payload = {**self.valid_payload}
        del payload['nom']
        resp = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Champ manquant', resp.json()['error'])

    def test_create_duplicate_numero(self):
        _make_diplome(numero_etudiant='ETU-VIEW-001')
        resp = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 409)

    def test_create_invalid_json(self):
        resp = self.client.post(
            self.url,
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_stores_annual_root(self):
        self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertTrue(AnnualRoot.objects.filter(annee=2024).exists())


class TamperDiplomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.diplome = _make_diplome()
        merkle.compute_and_store_annual_root(2024)
        self.url = reverse('tamper_diplome', args=[self.diplome.id])

    def test_tamper_changes_field(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({'mention': 'felicitations'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.diplome.refresh_from_db()
        self.assertEqual(self.diplome.mention, 'felicitations')

    def test_tamper_breaks_proof(self):
        """Après falsification, la preuve Merkle doit échouer."""
        tree, diplomes, _ = merkle.build_annual_tree(2024)
        root = merkle.get_root(tree)
        idx = next(i for i, d in enumerate(diplomes) if d.id == self.diplome.id)
        proof = merkle.generate_proof(tree, idx)

        # Falsifier
        self.client.post(
            self.url,
            data=json.dumps({'mention': 'felicitations'}),
            content_type='application/json',
        )
        self.diplome.refresh_from_db()
        new_hash = self.diplome.compute_hash()
        self.assertFalse(merkle.verify_proof(new_hash, proof, root))

    def test_tamper_rejects_disallowed_field(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({'nom': 'Hacker'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_tamper_404(self):
        resp = self.client.post(
            reverse('tamper_diplome', args=[9999]),
            data=json.dumps({'mention': 'bien'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)


class ApiRootViewTest(TestCase):
    def test_no_root(self):
        resp = self.client.get(reverse('api_root'))
        data = resp.json()
        self.assertIsNone(data['root'])
        self.assertEqual(data['tree_size'], 0)

    def test_with_root(self):
        RootHistory.objects.create(root_hash='abc123', tree_size=5)
        resp = self.client.get(reverse('api_root'))
        data = resp.json()
        self.assertEqual(data['root'], 'abc123')
        self.assertEqual(data['tree_size'], 5)


class ExportRootsViewTest(TestCase):
    def test_export_json(self):
        AnnualRoot.objects.create(annee=2024, root_hash='aaa', diploma_count=3)
        AnnualRoot.objects.create(annee=2023, root_hash='bbb', diploma_count=5)
        resp = self.client.get(reverse('export_roots'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['roots']), 2)
        self.assertIn('Content-Disposition', resp)
