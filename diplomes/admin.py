from django.contrib import admin
from .models import Diplome, MerkleLeaf, RootHistory, AnnualRoot


@admin.register(Diplome)
class DiplomeAdmin(admin.ModelAdmin):
    list_display  = ('numero_etudiant', 'nom', 'prenom', 'intitule', 'universite', 'mention', 'date_obtention')
    search_fields = ('numero_etudiant', 'nom', 'prenom', 'intitule', 'universite')
    list_filter   = ('universite', 'mention', 'date_obtention')


@admin.register(MerkleLeaf)
class MerkleLeafAdmin(admin.ModelAdmin):
    list_display  = ('leaf_index', 'diplome', 'leaf_hash')
    readonly_fields = ('leaf_hash',)


@admin.register(RootHistory)
class RootHistoryAdmin(admin.ModelAdmin):
    list_display    = ('root_hash', 'tree_size', 'created_at')
    readonly_fields = ('root_hash', 'tree_size', 'created_at')


@admin.register(AnnualRoot)
class AnnualRootAdmin(admin.ModelAdmin):
    list_display    = ('annee', 'root_hash', 'diploma_count', 'published_at')
    readonly_fields = ('root_hash', 'diploma_count', 'published_at')
