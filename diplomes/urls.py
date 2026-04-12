from django.urls import path

from .views import pages, api

urlpatterns = [
    # Pages HTML
    path('',                          pages.archives,        name='archives'),
    path('registre/',                 pages.dashboard,       name='dashboard'),
    path('diplomes/<int:diplome_id>/', pages.diplome_detail, name='diplome_detail'),

    # API JSON
    path('api/diplomes/',                         api.create_diplome,  name='create_diplome'),
    path('api/diplomes/<int:diplome_id>/tamper/',  api.tamper_diplome,  name='tamper_diplome'),
    path('api/root/',                              api.api_root,        name='api_root'),
    path('api/roots/export/',                      api.export_roots,    name='export_roots'),
]
