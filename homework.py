import logging
import sys
import time

from http import HTTPStatus
import requests
import telebot
from dotenv import dotenv_values

from exceptions import EndpointError

config = dotenv_values(".env")

PRACTICUM_TOKEN = config.get("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = config.get("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_token = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(list_token)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug(f"Бот отправил сообщение {message}")
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f"Ошибка при отправке сообщения: {error}")


def get_api_answer(timestamp):
    """Делает запрос к API."""
    params = {"from_date": timestamp}
    logging.info(f"Отправка запроса на {ENDPOINT} с параметрами {params}")
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise EndpointError(f"Ошибка запроса к API: {response.text}")
    except requests.RequestException as error:
        logging.error(f"Ошибка при запросе к API: {error}")
        return {}
    return response.json()


def check_response(response):
    """Проверяет ответ API."""
    if not response:
        message = "В ответе пришел пустой словарь."
        logging.error(message)
        raise KeyError(message)

    if not isinstance(response, dict):
        message = 'Тип ответа не соответствует "dict".'
        logging.error(message)
        raise TypeError(message)

    if "homeworks" not in response:
        message = 'В ответе отсутствует ключ "homeworks".'
        logging.error(message)
        raise KeyError(message)

    if not isinstance(response.get("homeworks"), list):
        message = "Формат ответа не соответствует списку."
        logging.error(message)
        raise TypeError(message)

    return response.get("homeworks")


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if "homework_name" not in homework or "status" not in homework:
        message = "Отсутствует необходимая информация о домашней работе."
        logging.error(message)
        raise KeyError(message)

    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        message = "Неизвестный статус домашней работы."
        logging.error(message)
        raise KeyError(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            "Отсутствуют токены. Программа была принудительно остановлена.")
        sys.exit("Нехватка токенов.")

    bot = telebot.TeleBot(TELEGRAM_TOKEN)  # Исправлено на правильный вызов
    timestamp = int(time.time())
    send_message(bot, "Я включился, отслеживаю изменения.")
    last_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    if last_message != message:
                        send_message(bot, message)
                        last_message = message
            else:
                logging.debug("Домашних работ нет.")
                continue
            timestamp = response.get("current_date", timestamp)
        except Exception as error:
            message = f"Ошибка в работе программы: {error}"
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler('my_logging.log')
        ]
    )
    main()
