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

from exeptions import ApiError

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

RETRY_PERIOD = 600
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
        logger.debug("Сообщение успешно отправлено")
    except telegram.error.TelegramError as send_message_error:
        logger.error('Ошибка отправки сообщения: %s', send_message_error)
        raise


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к API-сервису."""
    timestamp = current_timestamp if isinstance(
        current_timestamp, int) else int(time.time())

    params = {"from_date": timestamp}

    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params, timeout=10)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise ApiError(
                f"Ошибка: {HTTPStatus(homework_statuses.status_code).phrase}")
        return homework_statuses.json()
    except requests.RequestException as e:
        logger.error("Ошибка при запросе к API: %s", e)
        raise ApiError("Ошибка при запросе к API") from e


def check_response(response) -> Union[bool, dict]:
    """Проверка API на корректность."""
    if "homeworks" not in response or not response["homeworks"]:
        raise KeyError("Ответ API не содержит ключ 'homeworks'")
    if not isinstance(response["homeworks"], list):
        raise TypeError("Некорректный тип данных для 'homeworks'")
    return response["homeworks"]


def parse_status(homework: dict) -> str:
    """Функция извлекает информацию о конкретной домашней работе."""
    if "homework_name" not in homework or "status" not in homework:
        raise KeyError(
            "Ответ API не содержит необходимых ключей"
            "'homework_name' или 'status'")
    homework_name = homework["homework_name"]
    homework_status = homework["status"]

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise ValueError(
            f"Неизвестный статус домашней работы: {homework_status}")

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Функция проверяет доступность обязательных переменных."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(tokens):
        missing = [name for name, value in zip(["PRACTICUM_TOKEN",
                                                "TELEGRAM_TOKEN",
                                                "TELEGRAM_CHAT_ID"],
                                               tokens) if not value]
        for token_name in missing:
            logger.critical(
                "Отсутствует обязательная переменная окружения: %s",
                token_name)
        return False
    return True


def get_bot() -> telegram.Bot:
    """Инициализирует бота."""
    try:
        return telegram.Bot(token=TELEGRAM_TOKEN)
    except telegram.error.TelegramError as e:
        logger.error("Ошибка инициализации Telegram: %s", e)
        sys.exit()


def process_homework(bot: telegram.Bot, current_timestamp: int) -> int:
    """Обрабатывает домашнюю работу, отправляет сообщение в Telegram."""
    response = get_api_answer(current_timestamp)
    homeworks = check_response(response)
    if homeworks:
        message = parse_status(homeworks[0])
        send_message(bot, message)
        current_timestamp = response.get("current_date", current_timestamp)
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
            time.sleep(RETRY_PERIOD)
        except Exception as e:
            logger.error("Сбой в работе программы: %s", e)
            send_message(bot, f"Сбой в работе программы: {e}")
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
