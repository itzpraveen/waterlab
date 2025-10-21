"""
URL configuration for waterlab project.

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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include  # Added include
from django.views.generic import RedirectView
# from django.contrib.auth.views import LogoutView # Not used directly here

urlpatterns = [
    path('admin/', admin.site.urls),
    # Serve service worker from root by redirecting to static asset
    path('sw.js', RedirectView.as_view(url='/static/sw.js', permanent=True)),
    path('', include('core.urls', namespace='core')),
]

if settings.MEDIA_URL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
