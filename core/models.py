from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- 食材モデル ---
class Ingredient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    name = models.CharField(max_length=100, default='', verbose_name="食材名")
    quantity = models.CharField(max_length=50, default='', verbose_name="量")
    expiry_date = models.DateField(default=timezone.now, verbose_name="期限")

    def __str__(self):
        return self.name

# --- 体調モデル ---
class HealthCondition(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    condition = models.CharField(max_length=200, default='', verbose_name="健康状態")
    date = models.DateField(default=timezone.now, verbose_name="登録日")

    def __str__(self):
        return f"{self.user.username} - {self.date}"

# --- 楽天レシピのマスターデータ ---
class Recipe(models.Model):
    """楽天レシピから取得したマスターデータ（既存のテーブルをそのまま使用）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    recipeId = models.IntegerField(unique=True, null=True, blank=True)
    title = models.CharField(max_length=255)
    catch_copy = models.TextField(blank=True)
    foodImageUrl = models.URLField(max_length=500, blank=True)
    recipeUrl = models.URLField(max_length=500, blank=True)
    recipeCost = models.CharField(max_length=100, blank=True)
    ingredients = models.JSONField(default=list)
    instructions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# --- ユーザーが保存したレシピ（新規追加）---
class SavedRecipe(models.Model):
    """ユーザーが保存したレシピ"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    recipeId = models.CharField(max_length=50)  # UNIQUE制約なし
    title = models.CharField(max_length=255)
    catch_copy = models.TextField(blank=True, null=True)
    foodImageUrl = models.URLField(max_length=500, blank=True, null=True)
    recipeUrl = models.URLField(max_length=500, blank=True, null=True)
    recipeCost = models.CharField(max_length=100, blank=True, null=True)
    ingredients = models.JSONField(default=list)
    instructions = models.JSONField(default=list)
    recommendation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    main_nutrients = models.JSONField(default=list, blank=True, null=True)
    cooking_point = models.TextField(blank=True, null=True)
    
    class Meta:
        # ユーザーごとに同じrecipeIdを保存できるが、1ユーザーにつき1回のみ
        unique_together = ['user', 'recipeId']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)
    published = models.DateField()

    def __str__(self):
        return self.title