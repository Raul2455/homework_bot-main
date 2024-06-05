import random
import string
from datetime import datetime

import pytest
import homework


@pytest.fixture
def random_timestamp():
    """Генерирует случайную временную метку."""
    left_ts = 1000198000
    right_ts = 1000198991
    return random.randint(left_ts, right_ts)


@pytest.fixture
def current_timestamp():
    """Генерирует текущую временную метку."""
    return int(datetime.now().timestamp())


@pytest.fixture
def homework_module():
    """Возвращает модуль homework."""
    return homework


@pytest.fixture
def random_message():
    """Генерирует случайную строку."""
    def random_string(string_length=15):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(string_length))
    return random_string()


@pytest.fixture
def api_url():
    """Возвращает URL API."""
    return 'https://practicum.yandex.ru/api/user_api/homework_statuses/'


@pytest.fixture
def bot_token():
    """Возвращает токен бота."""
    return '123456789:ABCDE1234567890'


@pytest.fixture
def chat_id():
    """Возвращает ID чата."""
    return 123456789


@pytest.fixture
def message():
    """Возвращает тестовое сообщение."""
    return 'Тестовое сообщение'
