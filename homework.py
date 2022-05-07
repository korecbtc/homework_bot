import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiAnswerError, NotFoundTokens, WrongHomeworkStatus

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

previos_message = ''


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    global previos_message
    try:
        if message != previos_message:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logger.info('Сообщение отправлено в Телеграм')
            previos_message = message
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения в Телеграм: {error}')


def get_api_answer(current_timestamp):
    """Отправляю запрос API."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        message = 'Ошибка при запросе к основному API.'
        logger.error(message)
        send_message(bot, message)
        raise ApiAnswerError(message)
    logger.debug('Получен ответ от сервера')
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if type(response) is not dict:
        message = 'Ответ сервера имеет не верный тип данных.'
        logger.error(message)
        send_message(bot, message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'В ответе сервера отсутствуют необходимые ключи.'
        logger.error(message)
        send_message(bot, message)
        raise KeyError(message)
    homeworks = response['homeworks']
    if type(homeworks) is not list:
        message = 'В ответе сервера имеется не верный тип данных.'
        logger.error(message)
        send_message(bot, message)
        raise TypeError(message)
    logger.debug('Ответ от сервера корректен')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if 'homework_name' not in homework:
        message = 'В ответе сервера отсутствуют необходимые ключи'
        logger.error(message)
        send_message(bot, message)
        raise KeyError(message)
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Получен не корректный статус работы'
        logger.error(message)
        send_message(bot, message)
        raise WrongHomeworkStatus(message)
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяю токены на доступность."""
    if (
        TELEGRAM_CHAT_ID is None or TELEGRAM_TOKEN
        is None or PRACTICUM_TOKEN is None
    ):
        logger.critical('Недоступна как минимум одна из переменных окружения')
        return False
    else:
        logger.debug('Переменные окружения доступны')
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NotFoundTokens(
            'Завершение работы бота из-за отсутствия переменных окружения'
        )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    homework = check_response(get_api_answer(
        current_timestamp - ONE_MONTH_IN_SEC
    ))
    while True:
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
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
