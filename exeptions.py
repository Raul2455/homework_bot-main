from telegram import TelegramError


class BotKeyError(KeyError):
    """Ошибка возникает в случае отсутствия ключа словаря.
    В аргументах указывается проверяемый словарь и имя ключа.
    """

    def __init__(self, dictionary, key):
        """
        Инициализация ошибки.

        Args:
            dictionary (dict): Словарь, в котором произошла ошибка.
            key: Ключ, отсутствующий в словаре.
        """
        self.dictionary = dictionary
        self.key = key

    def __str__(self):
        """
        Возвращает строковое представление ошибки.

        Returns:
            str: Описание ошибки.
        """
        return f'в словаре {self.dictionary} нет ключа "{self.key}"!'


class BotTypeError(TypeError):
    """Ошибка возникает в случае несоответствия типов данных.
    В аргументах указывается проверяемый объект и ожидаемый тип данных.
    """

    def __init__(self, obj, expected_type):
        """
        Инициализация ошибки.

        Args:
            obj: Объект с некорректным типом данных.
            expected_type (type): Ожидаемый тип данных.
        """
        self.obj = obj
        self.expected_type = expected_type

    def __str__(self):
        """
        Возвращает строковое представление ошибки.

        Returns:
            str: Описание ошибки.
        """
        return f"тип данных {self.obj} не '{self.expected_type}'!"


class ResponseError(Exception):
    """Базовый класс для ошибок, связанных с ответами."""

    pass


class SendMessageError(TelegramError):
    """Ошибка возникает при отправке сообщения через Telegram."""

    pass
