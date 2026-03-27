from django.urls import path
from . import views

urlpatterns = [
    # Pages HTML
    path('',                                      views.archives,        name='archives'),
    path('registre/',                             views.dashboard,       name='dashboard'),
    path('diplomes/<int:diplome_id>/',            views.diplome_detail,  name='diplome_detail'),

    # API JSON
    path('api/diplomes/',                         views.create_diplome,  name='create_diplome'),
    path('api/diplomes/<int:diplome_id>/tamper/', views.tamper_diplome,  name='tamper_diplome'),
    path('api/root/',                             views.api_root,        name='api_root'),
    path('api/roots/export/',                     views.export_roots,    name='export_roots'),
]
