"""Основной модуль бота для проверки статусов домашних работ."""

import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Union

import requests
import telegram
from dotenv import load_dotenv

from exeptions import ApiError, ParseNoneStatus, TelegramBot, TokenError

load_dotenv()

logging.basicConfig(
    datefmt="%H:%M:%S",
    filename="main.log",
    encoding="UTF-8",
    filemode="a",
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(funcName)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s (%(funcName)s | %(lineno)d)"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot: telegram.Bot, message: str):
    """Функция отправляет сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info("Сообщение успешно отправлено")
    except Exception as send_message_error:
        logger.error(f'Ошибка отправки сообщения: {send_message_error}')
        raise


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к API-сервису."""
    if not isinstance(current_timestamp, (int, float)):
        timestamp = int(time.time())
        logger.error(
            'В функцию %s передано неверное значение current_timestamp: %s. '
            'Исправляю на текущее время %s',
            get_api_answer.__name__,
            current_timestamp,
            timestamp,
        )
    else:
        timestamp = current_timestamp

    params = {"from_date": timestamp}

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params, timeout=10
        )
        homework_status_code = homework_statuses.status_code
        if homework_status_code != HTTPStatus.OK:
            raise ApiError(
                f"Ошибка: {HTTPStatus(homework_status_code).phrase}"
            )
        else:
            homework_statuses = homework_statuses.json()
    except requests.ConnectionError as e:
        error_message = "OOPS!! ошибка соединения."
        raise ApiError(error_message) from e
    except requests.Timeout as e:
        error_message = "OOPS!! Ошибка тайм-аута"
        raise ApiError(error_message) from e
    except requests.RequestException as e:
        error_message = "OOPS!! General Error"
        raise ApiError(error_message) from e
    except KeyboardInterrupt as exc:
        error_message = "Кто-то закрыл программу"
        raise ApiError(error_message) from exc
    except Exception as requests_error:
        raise ApiError(
            f"Возникла ошибка при обращении к API [{requests_error}]"
        ) from requests_error
    else:
        return homework_statuses


def check_response(response) -> Union[bool, dict]:
    """Проверка API на корректность."""
    if not response["homeworks"]:
        return False
    elif not isinstance(response["homeworks"], list):
        raise TokenError
    else:
        return response["homeworks"]


def parse_status(homework: dict) -> Union[bool, str]:
    """Функция извлекает информацию о конкретной домашней работе."""
    if homework:
        homework_name = homework["homework_name"]
        homework_status = homework["status"]
    else:
        return False

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as exc:
        raise ParseNoneStatus from exc

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Функция проверяет доступность обязательных переменных."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(tokens):
        return True
    else:
        missing = [name for name, value in zip(["PRACTICUM_TOKEN",
                                                "TELEGRAM_TOKEN",
                                                "TELEGRAM_CHAT_ID"],
                                               tokens) if not value]
        for token_name in missing:
            logger.critical(
                f"Отсутствует обязательная переменная окружения: {token_name}")
        return False


def get_bot() -> telegram.Bot:
    """Инициализирует бота."""
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except telegram.error.Unauthorized as error_authorized:
        logger.critical("Ошибка при авторизации в Telegram: %s",
                        error_authorized)
        sys.exit()
    except telegram.error.TelegramError as error:
        logger.error("Ошибка инициализации Telegram: %s", error)
        sys.exit()
    return bot


def process_homework(bot: telegram, current_timestamp: int) -> int:
    """Обрабатывает домашнюю работу, отправляет сообщение в Telegram."""
    try:
        response = get_api_answer(current_timestamp)
        check = check_response(response)
        if check:
            status_homework = parse_status(check[0])
            send_message(bot, status_homework)
            logger.info("Сообщение с новым статусом отправлено")
            current_timestamp = response["current_date"]
        else:
            logger.debug("В ответе нет изменений")
    except TelegramBot as telegram_bot_error:
        logger.error(
            "Возникла ошибка с отправкой сообщения: %s", telegram_bot_error,
        )
    except ParseNoneStatus as error_status:
        message = (
            f"Сбой в работе, недокументированный статус домашней "
            f"работы, обнаруженный в ответе API: {error_status}"
        )
        logger.error(message)
        send_message(bot, message)
        logger.info("Отправка ошибки ParseNoneStatus")
    except TokenError as error_token:
        message = f"Отсутствие ожидаемых ключей от API: {error_token}"
        logger.error(message)
        send_message(bot, message)
        logger.info("Отправка ошибки TokenError")
    except ApiError as error_api:
        message = f"Нет доступа к API: {error_api}"
        logger.error(message)
        send_message(bot, message)
        logger.info("Отправка ошибки ApiError")
    except (requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            KeyboardInterrupt) as error:
        message = f"Сбой в работе программы: {error}"
        logger.error(message)
        send_message(bot, message)
        logger.info("Отправка ошибки при обращении к API")
    return current_timestamp


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    bot = get_bot()
    current_timestamp = int(time.time())

    while True:
        try:
            current_timestamp = process_homework(bot, current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(f"Сбой в работе программы: {error}")
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
