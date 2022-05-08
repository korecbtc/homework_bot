class WrongHomeworkStatus(Exception):
    """Исключение для некорректного статуса."""

    pass


class ApiAnswerError(Exception):
    """Исключение для некорректного ответа сервера."""

    pass


class MessageNotSent(Exception):
    """Исключение для неотправленного сообщения."""

    pass
