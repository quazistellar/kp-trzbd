"""
URL configuration for unireax_root project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include

from .settings import DEBUG, MEDIA_URL, MEDIA_ROOT

from unireax_main.metrics_view import prometheus_metrics_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('unireax_main.urls')),
    path('prometheus/metrics', prometheus_metrics_view, name='prometheus-metrics'),
    path('api/', include('api_unireax.urls'))
]

handler403 = 'unireax_main.views.custom_403'
handler404 = 'unireax_main.views.custom_404'
handler500 = 'unireax_main.views.custom_500'

if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)

if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, insecure=True)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, insecure=True)