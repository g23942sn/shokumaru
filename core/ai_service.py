import google.generativeai as genai
from django.conf import settings
import json
import re

# settings.pyに保存しておいたAPIキーを設定
genai.configure(api_key=settings.GEMINI_API_KEY)


#AIに渡すプロンプトを渡す
def generate_recipes_with_ai(ingredients, health_condition, current_weather):
    """
    食材、体調、天気の情報ををもとに、3つのレシピを提案させる関数
    """
    generation_config = genai.types.GenerationConfig(
        temperature=0.8 
    )
    #Geminiのモデル
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config=generation_config
    )
    
    # ホームページからの一般的なリクエストかどうかを判断
    # 不特定多数の訪問者
    if ingredients == "指定なし":
        # ホームページ用の、季節や天気に焦点を当てたプロンプト
        prompt = f"""
        あなたは人気の料理雑誌の編集長です。
        日本の現在の季節（晩夏）と、以下の「今日の天気」の情報だけを考慮して、読者の料理意欲を刺激する、創造的で全く異なるスタイルの人気レシピを3つ提案してください。

        # 今日の天気
        {current_weather}

        # レシピ提案のルール
        - ユーザー個人の冷蔵庫の中身は考慮せず、一般的に人気のあるレシピを提案してください。
        - 和食、洋食、中華など、異なるジャンルのレシピを提案してください。

        # 出力に関する厳格なルール
        - 必ず、3つのレシピオブジェクトを含む有効なJSON配列を返してください。
        - JSON配列の外には、いかなるテキスト、説明、マークダウンも含めないでください。

        # JSONフォーマット
        [
          {{
            "title": "string",
            "catch_copy": "string (なぜこのレシピがおすすめなのか、理由を添えたキャッチコピー)",
            "main_ingredients": "string (この料理の主要食材3つの箇条書き)",
            "nutrients": "string (摂取できる主な栄養素の箇条書き)",
            "cooking_point": "string (調理のポイントやコツ)",
            "ingredients": "string (すべての材料リスト)",
            "instructions": "string (作り方の手順)"
          }}
        ]
        """
    else:
        # 既存の、ユーザーの食材に基づくパーソナルなレシピ提案用のプロンプト
        # 在庫食材や体調を入力した特定のユーザー向け
        prompt = f"""
        あなたはユーザーの健康と食生活を支える、経験豊富なAIシェフ兼栄養管理士です。
        以下の3つの重要な情報に基づいて、ユーザーが本当に喜ぶ、創造的で全く異なるスタイルのレシピを3つ提案してください。

        # 1. 在庫食材リスト（最優先事項）
        {ingredients}

        # 2. ユーザーの現在の体調・気分
        {health_condition}

        # 3. 今日の天気
        {current_weather}

        # レシピ提案のルール
        - 上記の3つの要素を総合的（在庫食材、体調、天気）に考慮してください。特に、食材の消費を最優先してください。
        - 和食、洋食、中華など、異なるジャンルのレシピを提案してください。
        - 提案する3つのレシピは、互いに内容が重複しないようにしてください。
        - 提案するレシピは三日間被りのないようにしてください。
        - キャッチコピーは提案理由が明確に伝わるように作成してください。また、提案の根拠を具体的に記述してください。
        - 作り方の手順は、番号付きのステップごとの配列（リスト）として、どの材料をどのタイミングで使うかが明確にわかるように記述してください。

        # 出力に関する厳格なルール
        - 必ず、3つのレシピオブジェクトを含む有効なJSON配列を返してください。
        - JSON配列の外には、いかなるテキスト、説明、マークダウンも含めないでください。

        # JSONフォーマット
        [
          {{
            "title": "string",
            "catch_copy": "string (なぜこのレシピがおすすめなのか、理由を添えたキャッチコピー)",
            "main_ingredients": "string (消費を優先した主要食材3つの箇条書き)",
            "nutrients": "string (摂取できる主な栄養素の箇条書き)",
            "cooking_point": "string (調理のポイントやコツ)",
            "ingredients": [
                {{"name": "豚バラ薄切り肉", "quantity": "200g"}},
                {{"name": "白菜", "quantity": "1/4個"}},
                {{"name": "長ネギ", "quantity": "1/2本"}},
                {{"name": "生姜（すりおろし）", "quantity": "小さじ1"}},
                {{"name": "鶏がらスープの素", "quantity": "大さじ1"}},
                {{"name": "ごま油", "quantity": "大さじ1"}},
                {{"name": "塩・こしょう", "quantity": "少々"}}
               ],
            "instructions": [
                "白菜は1枚ずつはがし、豚バラ肉は長さを半分に切る。長ネギは斜め薄切りにする。",
                "鍋に白菜の半量を敷き詰め、その上に豚バラ肉の半量を広げて塩・こしょうを振る。これをもう一度繰り返す。",
                "長ネギと生姜を乗せ、鶏がらスープの素と水100ml（分量外）を回しかける。",
                "蓋をして中火にかけ、沸騰したら弱火で10〜15分ほど、白菜がくたっとなるまで蒸し煮にする。",
                "最後にごま油を回しかけて、全体をさっと混ぜ合わせたら完成。"
              ]
          }}
        ]
        """
    #実際にGeminiを呼び出して、プロンプトを渡している。ここでAPIと通信している。
    try:
        response = model.generate_content(prompt)
        
        print("--- AIからの生の応答 ---")
        print(response.text)
        print("--------------------------");

        #応答からJSONデータ本体だけ抜き出す
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            json_str = match.group(0)
            #DjangoやFlutterが理解できるデータ構造に変換
            recipes_json = json.loads(json_str)
            return recipes_json
        else:
            print("AIの応答からJSONを抽出できませんでした。")
            return None
        
    except Exception as e:
        print(f"AIレシピ生成中にエラーが発生しました: {e}")
        return None