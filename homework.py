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
previos_message = ''


def check_doubles(func):
    """Декоратор для отсеченеия повторных сообщений."""
    def wr(bot, message):
        # Сергей, подскажи, пожалуйста, как обойтись без глобальной переменной?
        # И почему их лучше не использовать?
        global previos_message
        if message != previos_message:
            func(bot, message)
            previos_message = message
            return previos_message
    return wr


@check_doubles
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
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
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
    if type(homeworks) is not list:
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


def log_and_send(bot, error):
    """Логирую и отправляю сообщение."""
    message = f'Сбой в работе программы: {error}'
    logger.error(message)
    send_message(bot, message)


def main():
    """Основная логика работы бота."""
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
        log_and_send(bot, error)
    except TypeError as error:
        log_and_send(bot, error)
    except KeyError as error:
        log_and_send(bot, error)
    except WrongHomeworkStatus as error:
        log_and_send(bot, error)
    except Exception as error:
        log_and_send(bot, error)

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
            log_and_send(bot, error)
        except TypeError as error:
            log_and_send(bot, error)
        except KeyError as error:
            log_and_send(bot, error)
        except WrongHomeworkStatus as error:
            log_and_send(bot, error)
        except Exception as error:
            log_and_send(bot, error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
