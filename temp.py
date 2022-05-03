import os
from dotenv import load_dotenv
import time
import requests
from exceptions import NotFoundTokens, ApiNotCorrect, NotResponseFromApi
load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}



def check_tokens():
    try:
        PRACTICUM_TOKEN + TELEGRAM_TOKEN + TELEGRAM_CHAT_ID
        return True
    except:
        return False

def get_api_answer(current_timestamp):
    """Отправляю запрос API"""
    try:
        timestamp = current_timestamp
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response = response.json()
        return response
    except:
        raise NotResponseFromApi('Сервер не отвечает')



def check_response(response):
    try:
        homeworks = response['homeworks']
        return homeworks
    except:
        raise ApiNotCorrect('Ответ сервера не корректен')
    
def parse_status(homework):
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'
       
        
current_timestamp = int(time.time())
homework = check_response(get_api_answer(int(time.time()) - RETRY_TIME*6*24*20))

check_tokens()

print(parse_status(homework[0]))

