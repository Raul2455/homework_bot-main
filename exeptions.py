class ApiError(Exception):
    """Ошибка при обращении к API."""

    def __init__(self, message, *args):
        """
        Инициализация исключения ApiError.

        :param message: Сообщение об ошибке
        :type message: str
        """
        super().__init__(message, *args)


class TokenError(Exception):
    """Ошибка при отсутствии токенов."""

    def __init__(self, message, *args):
        """
        Инициализация исключения TokenError.

        :param message: Сообщение об ошибке
        :type message: str
        """
        super().__init__(message, *args)


class ParseNoneStatus(Exception):
    """Ошибка при получении недокументированного статуса."""

    def __init__(self, message, *args):
        """
        Инициализация исключения ParseNoneStatus.

        :param message: Сообщение об ошибке
        :type message: str
        """
        super().__init__(message, *args)


class TelegramBot(Exception):
    """Ошибка при отправке сообщения в Telegram."""

    def __init__(self, message, *args):
        """
        Инициализация исключения TelegramBot.

        :param message: Сообщение об ошибке
        :type message: str
        """
        super().__init__(message, *args)
