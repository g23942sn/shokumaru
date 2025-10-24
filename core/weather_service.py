import requests
from django.conf import settings
from decouple import config

def get_current_weather(city="Tokyo"):
    """
    指定された都市の現在の天気を取得する関数
    """
    api_key = getattr(settings, 'WEATHER_API_KEY', None)
    if not api_key:
        return "天気情報なし (APIキー未設定)"

    # APIのエンドポイントURL
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},JP&appid={api_key}&lang=ja&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        data = response.json()
        
        # 例: "晴れ, 25.5°C" のような形式で返す
        description = data['weather'][0]['description']
        temp = data['main']['temp']
        return f"{description}, 気温{temp}°C"

    except requests.exceptions.RequestException as e:
        print(f"天気情報の取得に失敗しました: {e}")
        return "天気情報の取得に失敗"