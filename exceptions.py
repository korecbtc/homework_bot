class NotFoundTokens(Exception):
    """Исключение для переменных окружения."""

    pass


class WrongHomeworkStatus(Exception):
    """Исключение для некорректного статуса."""

    pass


class ApiAnswerError(Exception):
    """Исключение для некорректного ответа сервера."""

    pass
