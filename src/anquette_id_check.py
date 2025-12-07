import requests
from config import API_BASE_URL

def id_check(message):
    req = requests.get(f"{API_BASE_URL}/users/{message.from_user.id}")
    print(f'Проверка поиска пользователя для получения анкеты, код: {req.status_code}')
    data = req.json()
    return data['anquette_id']