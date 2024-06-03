"""Основной модуль бота для проверки статусов домашних работ."""

import datetime
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exeptions import (
    BotKeyError, BotTypeError, ResponseError, SendMessageError
)

PERIOD_IN_DAYS = 10
PERIOD = int(datetime.timedelta(days=PERIOD_IN_DAYS).total_seconds())

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
RETRY_PERIOD = RETRY_TIME
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Отправляется запрос')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение успешно отправлено')
    except telegram.error.TelegramError as error:
        logging.error(error, exc_info=True)
        logging.debug(f'send_message {error}')


def get_api_answer(current_timestamp):
    """
    Выполняет запрос к API.

    Параметры:
    current_timestamp (int): время, в которое выполняется запрос в формате Unix

    Возвращаемое значение:
    dict: ответ API преобразованный в формат словаря Python
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params=params, timeout=10
        )
        if response.status_code != HTTPStatus.OK:
            raise ResponseError(
                'Эндпойнт API "Практикум.Домашка" не доступен!'
            )
        return response.json()
    except requests.RequestException as error:
        raise ResponseError(f'Ошибка при запросе к API: {error}') from error


def check_response(response):
    """
    Проверяет, что ответ API является Python словарём.

    Параметры:
    response (dict): ответ API в формате словаря Python

    Возвращаемое значение:
    list: список домашних работ
    """
    if not isinstance(response, dict):
        raise BotTypeError(response, dict)

    if 'homeworks' not in response:
        raise BotKeyError(response, 'homeworks')

    if 'current_date' not in response:
        raise BotKeyError(response, 'current_date')

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise BotTypeError(homeworks, list)

    return homeworks


def parse_status(homework):
    """Извлекает статус проверки из домашней работы."""
    if 'status' not in homework:
        raise BotKeyError(homework, 'status')

    if 'homework_name' not in homework:
        raise BotKeyError(homework, 'homework_name')

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        raise BotKeyError(HOMEWORK_VERDICTS, homework_status)

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Проверяет наличие всех нужных переменных окружения (токенов).

    Возвращает:
    bool: True, если все токены присутствуют, иначе False.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения!')
        sys.exit('Отсутствуют переменные окружения!')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - PERIOD
    previous_error = None
    last_message = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
            else:
                logger.debug('Новых статусов нет.')

        except (BotTypeError, BotKeyError,
                ResponseError, SendMessageError) as error:
            message = f'Сбой в работе программы: {error}'
            if message != previous_error:
                logger.error(message)
                send_message(bot, message)
                previous_error = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
