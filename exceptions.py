"""
Этот модуль определяет пользовательские исключения.
для обработки ошибок API и проблем с форматом ответов.
"""


class EndpointError(Exception):
    """Исключение возникает, когда конечная точка API недоступна."""

    def __init__(self, response, message=None):
        """
        Инициализируйте исключение с помощью объекта.
        response и необязательного пользовательского сообщения.
        """
        if message is None:
            # Splitting the message to comply with line length requirements
            message = (f"Конечная точка {response.url} не доступна. "
                       f"Код ответа API: {response.status_code}")
        super().__init__(message)


class ResponseFormatError(Exception):
    """Исключение вызвано ошибками в формате ответа API."""

    def __init__(self, text):
        """Инициализируйте исключение описанием проблемы с форматированием."""
        message = f"Проверка ответа API: {text}"
        super().__init__(message)
