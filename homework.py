import os
from dotenv import load_dotenv
import time
import requests
from exceptions import NotResponseFromApi, ApiNotCorrect
import telegram
import logging
from logging.handlers import StreamHandler
load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ONE_MONTH_IN_SEC = 3600 * 24 * 30
LAST_HOMEWORK = 0
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)



def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Отправляю запрос API"""
    try:
        timestamp = current_timestamp
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response = response.json()
        return response
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        


def check_response(response):
    try:
        homeworks = response['homeworks']
        return homeworks
    except Exception as error:
        logging.error(f'Ответ сервера не корректен: {error}')
        


def parse_status(homework):
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяю токены на доступность"""
    try:
        PRACTICUM_TOKEN + TELEGRAM_TOKEN + TELEGRAM_CHAT_ID
        return True
    except Exception as error:
        logging.error(f'Недоступна переменная окружения: {error}')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homework = check_response(get_api_answer(current_timestamp - ONE_MONTH_IN_SEC))
    while check_tokens():
        try:
            if homework != check_response(get_api_answer(current_timestamp - ONE_MONTH_IN_SEC)):
                homework = check_response(get_api_answer(current_timestamp - ONE_MONTH_IN_SEC))
                send_message(bot, parse_status(homework[LAST_HOMEWORK]))
                

            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)

if __name__ == '__main__':
    main()
