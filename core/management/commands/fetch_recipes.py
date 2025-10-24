import requests
import time
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Recipe

class Command(BaseCommand):
    help = '楽天レシピAPIから効率的に人気レシピを取得し、データベースに保存します。'

    def handle(self, *args, **options):
        if not hasattr(settings, 'RAKUTEN_APP_ID'):
            self.stdout.write(self.style.ERROR('settings.pyにRAKUTEN_APP_IDが設定されていません。'))
            return

        APPLICATION_ID = settings.RAKUTEN_APP_ID
        
        # ### ステップ1: カテゴリ取得をシンプルかつ効率的に ###
        self.stdout.write("主要な中カテゴリの一覧を取得中...")
        category_list_url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426"
        
        # まずは大カテゴリのIDリストを取得
        large_params = {"applicationId": APPLICATION_ID, "categoryType": "large", "formatVersion": 2}
        try:
            large_res = requests.get(category_list_url, params=large_params).json()
            large_category_ids = [cat['categoryId'] for cat in large_res.get('result', {}).get('large', [])]
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"大カテゴリの取得に失敗しました: {e}"))
            return
        
        time.sleep(1)

        # 全ての中カテゴリIDを取得
        medium_categories = []
        for large_id in large_category_ids:
            medium_params = {"applicationId": APPLICATION_ID, "categoryType": "medium", "parentCategoryId": large_id, "formatVersion": 2}
            try:
                medium_res = requests.get(category_list_url, params=medium_params).json()
                if 'result' in medium_res and 'medium' in medium_res['result']:
                    for med_cat in medium_res['result']['medium']:
                        # ランキング取得に使えるカテゴリID (large-medium) をリストに追加
                        medium_categories.append(f"{med_cat['parentCategoryId']}-{med_cat['categoryId']}")
                time.sleep(1) # APIへの負荷を考慮
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.WARNING(f"中カテゴリ(親:{large_id})の取得中にエラー: {e} - スキップします。"))


        self.stdout.write(self.style.SUCCESS(f"有効な中カテゴリIDを {len(medium_categories)}件 取得しました。"))

        # ### ステップ2: レシピ取得を効率的に ###
        self.stdout.write("人気レシピの取得を開始します... (完了まで数分〜十数分かかります)")
        newly_created_count = 0
        total_checked_count = 0
        ranking_url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"

        for i, category_id in enumerate(medium_categories):
            self.stdout.write(f"({i+1}/{len(medium_categories)}) カテゴリID: {category_id} のレシピを取得中...")
            params = {"applicationId": APPLICATION_ID, "categoryId": category_id, "formatVersion": 2}
            try:
                res = requests.get(ranking_url, params=params, timeout=10)
                res.raise_for_status() 
                recipes_data = res.json().get('result', [])

                for recipe_data in recipes_data:
                    total_checked_count += 1
                    # 既にDBに存在するレシピは更新、なければ新規作成する
                    obj, created = Recipe.objects.update_or_create(
                        recipeId=recipe_data.get('recipeId'),
                        defaults={
                            'title': recipe_data.get('recipeTitle'),
                            'catch_copy': recipe_data.get('recipeDescription'),
                            'foodImageUrl': recipe_data.get('foodImageUrl'),
                            'recipeUrl': recipe_data.get('recipeUrl'),
                            'recipeCost': recipe_data.get('recipeCost'),
                            'ingredients': json.dumps(recipe_data.get('recipeMaterial', []), ensure_ascii=False),
                            'instructions': json.dumps([]),
                        }
                    )
                    if created:
                        newly_created_count += 1
                
                time.sleep(2)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    self.stdout.write(self.style.WARNING("APIリクエストが多すぎます。60秒待機します..."))
                    time.sleep(60)
                else:
                    self.stdout.write(self.style.ERROR(f"HTTPエラー ({category_id}): {e} - スキップします。"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"予期せぬエラーが発生しました ({category_id}): {e} - スキップします。"))

        self.stdout.write(self.style.SUCCESS(f"処理が完了しました。{total_checked_count}件のレシピをチェックし、新たに{newly_created_count}件をデータベースに保存しました。"))

