"""Модуль для отслеживания статуса домашних работ через Telegram бота."""

from http import HTTPStatus
import logging
import sys
import time

import requests
from dotenv import dotenv_values
from telebot import TeleBot, apihelper

config = dotenv_values(".env")

PRACTICUM_TOKEN = config.get("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = config.get("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600  # Период повторных запросов к API в секундах
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
TIMEOUT = 10  # Таймаут для запросов к API

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    missing_tokens = [token for token in tokens if not globals().get(token)]
    if missing_tokens:
        missing = ', '.join(missing_tokens)
        error_message = f"Отсутствуют токены: {missing}."
        logging.critical(error_message)
        sys.exit(f"Нехватка токенов: {missing}.")


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f"Бот отправил сообщение: {message}")
    except apihelper.ApiException as error:
        logging.error(f"Ошибка при отправке сообщения: {error}")
        raise


def get_api_answer(timestamp):
    """Делает запрос к API."""
    params = {"from_date": timestamp}
    logging.info(f"Отправка запроса на {ENDPOINT} с параметрами {params}")

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise RuntimeError(f"Ошибка при запросе к API: {error}")

    if response.status_code != HTTPStatus.OK:
        raise ValueError(f"Ошибка запроса к API: {response.text}")

    return response.json()


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        raise TypeError(f'Тип ответа не "dict", получен {type(response)}')
    if "homeworks" not in response:
        raise KeyError('В ответе нет ключа "homeworks".')
    if not isinstance(response.get("homeworks"), list):
        raise TypeError(
            f"Формат ответа не список,"
            f"получен {type(response.get('homeworks'))}."
        )
    return response["homeworks"]


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if "homework_name" not in homework or "status" not in homework:
        raise KeyError("Отсутствует необходимая информация о домашней работе.")
    homework_name = homework["homework_name"]
    homework_status = homework["status"]
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise ValueError(
            f"Неизвестный статус домашней работы: {homework_status}"
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
                else:
                    logging.debug("Получено повторяющееся сообщение.")
            else:
                logging.debug("Домашних работ нет.")
            timestamp = response.get("current_date", timestamp)
        except Exception as error:
            error_message = f"Ошибка в работе программы: {error}"
            logging.error(error_message, exc_info=True)
            if last_message != error_message:
                try:
                    send_message(bot, error_message)
                    last_message = error_message
                except apihelper.ApiException:
                    logging.error("Ошибка при отправке сообщения"
                                  "об ошибке в Telegram")
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    format_str = (
        "%(asctime)s [%(levelname)s] %(message)s "
        "[%(funcName)s:%(lineno)d]"
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format=format_str,
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler('my_logging.log')
        ]
    )
    main()
