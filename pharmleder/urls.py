from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('lots.urls')),
    path('static/<path:path>', serve, {'document_root': settings.STATICFILES_DIRS[0]}),
]
