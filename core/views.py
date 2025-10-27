import datetime
import json
import re
import requests
import random
import operator
from functools import reduce

# Django関連
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q

# DRF関連
from rest_framework.decorators import api_view
from rest_framework.response import Response


# アプリ内のモデル、フォームなど
from .models import Recipe, Ingredient, HealthCondition, SavedRecipe, Book
from .forms import IngredientForm, HealthConditionForm
from .serializers import RecipeSerializer, SavedRecipeSerializer, BookSerializer
from rest_framework import viewsets
from . import weather_service

# Google Generative AI (Gemini)
import google.generativeai as genai
from django.conf import settings
genai.configure(api_key=settings.GEMINI_API_KEY)

NUM_SUGGESTED_RECIPES = 5


# ==============================================================================
#  AI ヘルパー関数
# ==============================================================================
def select_and_enrich_recipes_with_ai(recipe_candidates, user_ingredients, health_condition, current_weather):
    safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    
    model = genai.GenerativeModel('gemini-2.5-flash', safety_settings=safety_settings)
    
    random.shuffle(recipe_candidates)
    candidates_text = json.dumps(recipe_candidates[:20], ensure_ascii=False)

    prompt = f"""
    あなたはユーザーの健康と冷蔵庫の中身を完璧に把握している、最高の料理アドバイザーです。
    あなたの仕事は、以下の「レシピ候補リスト(JSON形式)」の中から、下記の「ユーザーの状況」を総合的に判断し、最もふさわしい最高のレシピを{NUM_SUGGESTED_RECIPES}つだけ選び出すことです。
    選び出したレシピそれぞれに、以下のキーを追加・生成してください。
    - "instructions": 最も一般的で分かりやすい作り方の手順（5〜8ステップの配列）
    - "recommendation_reason": 天気・体調・食材の観点から考えた、簡潔な選定理由（1〜2文）
    - "main_nutrients": そのレシピで主に摂取できる栄養素（3〜5つの文字列の配列）
    - "cooking_point": 調理の際に美味しく作るためのコツやポイント（簡潔な1文）

    # ユーザーの状況
    - 在庫食材リスト: {', '.join(user_ingredients)}
    - 現在の体調・気分: {health_condition}
    - 今日の天気: {current_weather}
    
    # レシピ候補リスト (JSON形式)
    {candidates_text}

    # ルール
    - 「在庫食材リスト」の食材を最も多く使っているレシピを最優先してください。
    - 次に「体調・気分」と「天気」を考慮して、最適なレシピを選んでください。
    - 選択するレシピは{NUM_SUGGESTED_RECIPES}つだけにしてください。
    - 必ず、選び出したレシピオブジェクトに "instructions", "recommendation_reason", "main_nutrients", "cooking_point" の4つのキーを正しく追加してください。
    - "main_nutrients" は必ず配列（リスト）形式にしてください。例: ["タンパク質", "ビタミンC", "食物繊維"]

    # 出力形式 (厳格なルール)
    - 必ず、あなたが選び、手順と理由を追加した{NUM_SUGGESTED_RECIPES}つのレシピオブジェクトを含む、有効なJSON配列のみを返してください。
    """
    try:
        response = model.generate_content(prompt)
        print("--- AIによる最終選考＆手順生成結果（生）---")
        print(response.text)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
    except Exception as e:
        print(f"AI処理中にエラー: {e}")
        return []

# ==============================================================================
#  Flutter用APIビュー
# ==============================================================================

@api_view(['GET'])
def suggest_recipes_api(request):
    """【Flutter用】ローカルDBから食材に合うレシピを検索し、AIが最終選考するAPI"""
    user = User.objects.first()
    if not user: return Response({'error': 'テストユーザーがいません。'}, status=404)

    all_ingredients = Ingredient.objects.filter(user=user).order_by('expiry_date')
    if not all_ingredients: return Response({'error': '食材が登録されていません。'}, status=400)
    
    ingredient_names = [ing.name for ing in all_ingredients]
    
    all_recipes_qs = Recipe.objects.all()
    
    scored_recipes = []
    for recipe in all_recipes_qs:
        try:
            recipe_materials = json.loads(recipe.ingredients)
        except json.JSONDecodeError:
            continue

        score = 0
        for i, user_ing in enumerate(ingredient_names):
            if any(user_ing in r_ing for r_ing in recipe_materials):
                score += (len(ingredient_names) - i)
        
        if score > 0:
            scored_recipes.append({"score": score, "recipe_obj": recipe})

    scored_recipes.sort(key=lambda x: x['score'], reverse=True)
    
    if not scored_recipes:
        return Response({'error': "在庫食材に合うレシピがデータベースに見つかりませんでした。"}, status=404)

    top_candidates_qs = [item['recipe_obj'] for item in scored_recipes[:30]]

    candidate_recipes = []
    for recipe in top_candidates_qs:
        candidate_recipes.append({
            "recipeId": str(recipe.recipeId),  # ★ str()で文字列に変換
            "recipeTitle": recipe.title,
            "recipeDescription": recipe.catch_copy or "",  # ★ Noneの場合は空文字
            "foodImageUrl": recipe.foodImageUrl or "",
            "recipeUrl": recipe.recipeUrl or "",
            "recipeCost": str(recipe.recipeCost) if recipe.recipeCost else "",  # ★ str()で変換
            "recipeMaterial": json.loads(recipe.ingredients),
        })
    
    print(f"データベースからスコアリングに基づき {len(candidate_recipes)}件 のレシピ候補を抽出しました。AIによる選考を開始します。")

    latest_health = HealthCondition.objects.filter(user=user).order_by('-date').first()
    health_text = latest_health.condition if latest_health else "特に指定なし"
    current_weather = weather_service.get_current_weather("Tokyo")
    
    final_recipes = select_and_enrich_recipes_with_ai(
        candidate_recipes,
        ingredient_names,
        health_text,
        current_weather
    )
    
    if not final_recipes: 
        random.shuffle(candidate_recipes)
        final_recipes = candidate_recipes[:NUM_SUGGESTED_RECIPES]
        for recipe in final_recipes: 
            recipe.setdefault('instructions', [])

    for recipe in final_recipes:
        user_ingredients_set = set(ingredient_names)
        recipe_materials_set = set(recipe.get('recipeMaterial', []))
        used = [u_ing for u_ing in user_ingredients_set for r_ing in recipe_materials_set if u_ing in r_ing]
        recipe['used_ingredients'] = list(set(used))
        
        # ★ 念のため、最終出力時も文字列であることを保証
        recipe['recipeId'] = str(recipe.get('recipeId', ''))
        recipe['recipeCost'] = str(recipe.get('recipeCost', ''))


    return Response({'recipes': final_recipes})


# ==============================================================================
#  Webページ用ビュー (変更なし)
# ==============================================================================
@login_required
def home(request):
    return redirect('ingredient_list')

# views.py の register_data 関数

@login_required
def register_data(request):
    """食材と体調を登録するページ"""
    if request.method == 'POST':
        # ↓ここから下の行をすべて一段インデントする
        ingredient_form = IngredientForm(request.POST)
        health_form = HealthConditionForm(request.POST)
        if ingredient_form.is_valid() and health_form.is_valid():
            # このif文の中身は、さらに深くインデントする
            ingredient = ingredient_form.save(commit=False)
            ingredient.user = request.user
            ingredient.save()
            health = health_form.save(commit=False)
            health.user = request.user
            health.save()
            return redirect('ingredient_list')
    else:
        ingredient_form = IngredientForm()
        health_form = HealthConditionForm()
    
    context = {'ingredient_form': ingredient_form, 'health_form': health_form}
    return render(request, 'core/register.html', context)

@login_required
def ingredient_list(request):
    ingredients = Ingredient.objects.filter(user=request.user).order_by('expiry_date')
    return render(request, 'core/ingredient_list.html', {'ingredients': ingredients})

@login_required
def delete_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id, user=request.user)
    if request.method == 'POST':
        ingredient.delete()
    return redirect('ingredient_list')

@login_required
def saved_recipe_list(request):
    saved_recipes = Recipe.objects.filter(user=request.user).order_by('-created_at')
    context = {'recipes': saved_recipes}
    return render(request, 'core/saved_recipe_list.html', context)

@login_required
def recipe_detail(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id, user=request.user)
    return render(request, 'core/recipe_detail.html', {'recipe': recipe})

# ==============================================================================
#  Flutter用APIビュー (変更なし)
# ==============================================================================

@api_view(['POST'])
def save_recipe_api(request):
    user = User.objects.first()
    data = request.data
    
    recipe_id = data.get('recipeId', '')
    
    # SavedRecipeで重複チェック
    existing_recipe = SavedRecipe.objects.filter(user=user, recipeId=recipe_id).first()
    
    if existing_recipe:
        return Response({'status': 'already_saved', 'message': 'このレシピは既に保存されています。'}, status=200)
    
    # SavedRecipeに保存
    SavedRecipe.objects.create(
        user=user,
        recipeId=recipe_id,
        title=data.get('recipeTitle', ''),
        catch_copy=data.get('recipeDescription', ''),
        foodImageUrl=data.get('foodImageUrl', ''),
        recipeUrl=data.get('recipeUrl', ''),
        recipeCost=data.get('recipeCost', ''),
        ingredients=data.get('recipeMaterial', []),  # JSONFieldなのでjson.dumpsは不要
        instructions=data.get('instructions', []),
        recommendation_reason=data.get('recommendation_reason', ''),
        main_nutrients=data.get('main_nutrients', []),
        cooking_point=data.get('cooking_point', '')
    )
    return Response({'status': 'success', 'message': 'レシピを保存しました！'}, status=200)


@api_view(['GET'])
def recipe_list_api(request):
    """保存したレシピ一覧を取得"""
    user = User.objects.first()
    saved_recipes = SavedRecipe.objects.filter(user=user).order_by('-created_at')
    
    recipes_data = []
    for recipe in saved_recipes:
        recipes_data.append({
            'id': recipe.id,
            'recipeId': str(recipe.recipeId),
            'recipeTitle': recipe.title,
            'recipeDescription': recipe.catch_copy or '',
            'foodImageUrl': recipe.foodImageUrl or '',
            'recipeUrl': recipe.recipeUrl or '',
            'recipeCost': str(recipe.recipeCost) if recipe.recipeCost else '',
            'recipeMaterial': recipe.ingredients,  # 既にリスト形式
            'instructions': recipe.instructions,  # 既にリスト形式
            'recommendation_reason': recipe.recommendation_reason or '',
            'main_nutrients': recipe.main_nutrients or [],
            'cooking_point': recipe.cooking_point or ''
        })
    
    return Response(recipes_data)

@api_view(['DELETE'])
def delete_recipe_api(request, recipe_id):
    """保存したレシピを削除"""
    user = User.objects.first()
    
    try:
        # idフィールド（整数の主キー）で検索
        recipe = SavedRecipe.objects.get(id=recipe_id, user=user)
        recipe_title = recipe.title
        recipe.delete()
        return Response({
            'status': 'success', 
            'message': f'「{recipe_title}」を削除しました'
        }, status=200)
    except SavedRecipe.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'レシピが見つかりません'
        }, status=404)
    except Exception as e:
        print(f"削除エラー: {e}")  # デバッグ用
        return Response({
            'status': 'error', 
            'message': f'削除中にエラーが発生しました: {str(e)}'
        }, status=500)


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Bookデータを表示するためのAPI
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer