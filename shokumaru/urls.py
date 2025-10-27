"""
URL configuration for shokumaru project.

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
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers # <--- DRFのルーターをインポート
from core import views as core_views

router = routers.DefaultRouter()

router.register(r'books', core_views.BookViewSet, basename='book')
router.register(r'recipes', core_views.RecipeViewSet, basename='recipe')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('accounts/', include('django.contrib.auth.urls')),
    #path('api/recipe/save/', views.save_recipe_api, name='save_recipe_api'),
]
