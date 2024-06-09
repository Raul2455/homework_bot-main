"""
Этот модуль определяет пользовательские исключения.
для обработки ошибок API и проблем с форматом ответов.
"""


class EndpointError(Exception):
    """Исключение возникает, когда конечная точка API недоступна."""

    def __init__(self, message=None, response=None):
        """
        Инициализируйте исключение.
        с необязательным пользовательским сообщением
        и объектом ответа.
        """
        if message is None and response is not None:
            message = (f"Конечная точка {response.url} не доступна. "
                       f"Код ответа API: {response.status_code}")
        elif message is None:
            message = "Ошибка доступа к конечной точке API."
        super().__init__(message)


class ResponseFormatError(Exception):
    """Исключение вызвано ошибками в формате ответа API."""

    def __init__(self, message):
        """Инициализируйте исключение с пользовательским сообщением."""
        super().__init__(message)
