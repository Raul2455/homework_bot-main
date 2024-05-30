"""Модуль для мониторинга статуса домашних работ через API Яндекс.
   Практикум и уведомления через Telegram.
"""

import json
import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
END_POINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': ('Работа проверена: ревьюеру всё понравилось. Ура!'),
    'reviewing': ('Работа взята на проверку ревьюером.'),
    'rejected': ('Работа проверена: у ревьюера есть замечания.')
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    handlers=[
        RotatingFileHandler('program.log', maxBytes=50000000, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы программы."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if not token:
            logger.critical(f'Отсутствует переменная окружения: {token}')
            return False
    logger.debug('Все токены получены успешно')
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info('Отправляется запрос на отправку сообщения')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено')
    except TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения: {error}', exc_info=True)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        if not isinstance(timestamp, int):
            raise TypeError('Timestamp должен быть целым числом')
        payload = {'from_date': timestamp}
        logger.info('Запрос к API')
        response = requests.get(
            END_POINT, headers=HEADERS, params=payload, timeout=10)
        if response.status_code != HTTPStatus.OK:
            logger.error(
                f'API возвращает код, отличный от 200: {response.status_code}')
            raise requests.exceptions.HTTPError(
                f'HTTPError: {response.status_code}')
        return response.json()
    except json.JSONDecodeError as error:
        logger.error(f'Не удалось обработать JSON: {error}')
        return None
    except requests.exceptions.RequestException as error:
        logger.error(f'Запрос недоступен: {error}')
        raise
    except TypeError as error:
        logger.error(f'Произошла ошибка: {error}')
        raise


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not response:
        logger.error('Нет ответа от сервера')
        raise ValueError('Пустой ответ от сервера')

    if not isinstance(response, dict):
        logger.error('Ответ API не является словарем')
        raise TypeError('Ответ API не является словарем')

    if 'homeworks' not in response:
        logger.error('В ответе API нет ключа "homeworks"')
        raise KeyError('В ответе API нет ключа "homeworks"')

    if not isinstance(response['homeworks'], list):
        logger.error('Домашние работы в ответе API не являются списком')
        raise TypeError('Домашние работы в ответе API не являются списком')

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы."""
    logger.debug('Начало парсинга статуса домашней работы')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status is None:
        raise KeyError('В ответе API отсутствует имя работы или статус')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise ValueError(
            f'Недокументированный статус домашней работы: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые переменные окружения')
        raise SystemExit(-1)
    bot = Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Старт бота')
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            timestamp = response.get('current_date', timestamp)
        except (requests.exceptions.RequestException, ValueError,
                TypeError, KeyError) as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
