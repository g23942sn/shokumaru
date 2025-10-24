from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


urlpatterns = [
    # Webページ用
    path('', views.home, name='home'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('register/', views.register_data, name='register'),
    path('ingredients/', views.ingredient_list, name='ingredient_list'),
    path('ingredient/delete/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('saved-recipes/', views.saved_recipe_list, name='saved_recipes'),
    
    # Flutterと連携するAPI用
    path('api/suggest/', views.suggest_recipes_api, name='suggest_recipes_api'),
    
    path('api/recipes/', views.recipe_list_api, name='recipe_list_api'),
    path('api/recipe/save/', views.save_recipe_api, name='save_recipe_api'),
    path('api/recipe/delete/<int:recipe_id>/', views.delete_recipe_api, name='delete_recipe_api'),  # 追加

    # Django認証用
    path('accounts/', include('django.contrib.auth.urls')),
] 