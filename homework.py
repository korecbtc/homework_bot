import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiAnswerError, MessageNotSent, WrongHomeworkStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
ONE_MONTH_IN_SEC = 3600 * 24 * 30
LAST_HOMEWORK = 0
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - '
    '%(funcName)s - %(lineno)d - %(message)s'
)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise MessageNotSent(
            f'Ошибка при отправке сообщения в Телеграм: {error}'
        )
    else:
        logger.info('Сообщение отправлено в Телеграм')


def get_api_answer(current_timestamp):
    """Отправляю запрос API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    PARAMS_FOR_REQUEST = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    try:
        response = requests.get(**PARAMS_FOR_REQUEST)
    except Exception as error:
        raise ApiAnswerError(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        raise ApiAnswerError('Ошибка при запросе к основному API.')
    logger.debug('Получен ответ от сервера')
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ сервера имеет не верный тип данных.')
    if ('homeworks' or 'current_date') not in response:
        raise KeyError('В ответе сервера отсутствуют необходимые ключи.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('В ответе сервера имеется не верный тип данных.')
    logger.debug('Ответ от сервера корректен')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе сервера отсутствуют необходимые ключи')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise WrongHomeworkStatus('Получен не корректный статус работы')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяю токены на доступность."""
    return all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN])


def log_and_send(bot, error, previos_message):
    """Логирую и отправляю сообщение, если оно уникально."""
    message = f'Сбой в работе программы: {error}'
    logger.error(message)
    if message != previos_message:
        send_message(bot, message)
        previos_message = message
    return previos_message

# Да, следующая функция лишняя, но иначе flake выдает ошибку
# "main is too complex (C901)"
# И работа не проходит проверку Яндекса.
# Поэтому, разбил на 2 функции
# С этой же целью сделал отдельную функцию для отправки
# сообщений и проверки дублей.


def do_homework():
    """Вспомогательная функция, иначе main is too complex (C901)."""
    previos_message = ''
    if not check_tokens():
        logger.critical('Недоступна как минимум одна из переменных окружения')
        sys.exit(1)
    logger.debug('Переменные окружения доступны')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    try:
        homework = check_response(get_api_answer(
            current_timestamp - ONE_MONTH_IN_SEC
        ))
    except ApiAnswerError as error:
        log_and_send(bot, error, previos_message)
    except TypeError as error:
        log_and_send(bot, error, previos_message)
    except KeyError as error:
        log_and_send(bot, error, previos_message)
    except WrongHomeworkStatus as error:
        log_and_send(bot, error, previos_message)
    except Exception as error:
        log_and_send(bot, error, previos_message)
    return homework


def main(homework):
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previos_message = ''
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
        except MessageNotSent as error:
            logger.error(error)
        except ApiAnswerError as error:
            previos_message = log_and_send(bot, error, previos_message)
        except TypeError as error:
            previos_message = log_and_send(bot, error, previos_message)
        except KeyError as error:
            previos_message = log_and_send(bot, error, previos_message)
        except WrongHomeworkStatus as error:
            previos_message = log_and_send(bot, error, previos_message)
        except Exception as error:
            previos_message = log_and_send(bot, error, previos_message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main(do_homework())
