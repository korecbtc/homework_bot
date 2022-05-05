import os
from dotenv import load_dotenv
import time
import requests
from exceptions import NotResponseFromApi, ApiNotCorrect
import telegram
import logging
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
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в Телеграм"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено в Телеграм')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения в Телеграм: {error}')


def get_api_answer(current_timestamp):
    """Отправляю запрос API"""
    try:
        timestamp = current_timestamp
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.debug('Получен ответ от сервера')
        response = response.json()
        return response
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверяет ответ API на корректность"""
    try:
        homeworks = response['homeworks']
        logger.debug('Ответ от сервера корректен')
        return homeworks
    except Exception as error:
        logger.error(f'Ответ сервера не корректен: {error}')


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы"""
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(
            f'Получен не корректный статус работы: {homework_status}'
        )
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяю токены на доступность"""
    if (
        TELEGRAM_CHAT_ID is None or TELEGRAM_TOKEN
        is None or PRACTICUM_TOKEN is None
    ):
        logger.critical('Недоступна одна из переменных окружения')
        return False
    else:
        logger.debug('Переменные окружения доступны')
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homework = check_response(get_api_answer(
        current_timestamp - ONE_MONTH_IN_SEC
    ))
    previos_message = ''
    while check_tokens():
        try:
            if homework != check_response(
                get_api_answer(current_timestamp - ONE_MONTH_IN_SEC)
            ):
                logger.debug('Статус работы изменился')
                homework = check_response(get_api_answer(
                    current_timestamp - ONE_MONTH_IN_SEC)
                )
                send_message(bot, parse_status(homework[LAST_HOMEWORK]))
            logger.debug('Обновлений не обнаружено')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != previos_message:
                send_message(bot, message)
                previos_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
