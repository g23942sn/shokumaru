from django.contrib import admin
from .models import Ingredient, HealthCondition, Recipe, SavedRecipe # Recipeをインポート

# Register your models here.
admin.site.register(Recipe) # Recipeモデルを管理画面に登録
admin.site.register(Ingredient)
admin.site.register(HealthCondition)
admin.site.register(SavedRecipe)