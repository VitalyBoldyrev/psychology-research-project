"""Форматирование сообщений бота."""


def progress_bar(current: int, total: int, length: int = 10) -> str:
    """Создать текстовый прогресс-бар.

    Пример: ▓▓▓▓▓▓░░░░ 60%
    """
    if total == 0:
        return '░' * length + ' 0%'

    filled = int(length * current / total)
    empty = length - filled
    percent = int(100 * current / total)

    return '▓' * filled + '░' * empty + f' {percent}%'


def format_question(
    question_num: int,
    total: int,
    question_text: str
) -> str:
    """Отформатировать текст вопроса с номером и прогрессом."""
    bar = progress_bar(question_num, total)

    return (
        f'📊 Вопрос {question_num} из {total}\n'
        f'{bar}\n\n'
        f'{question_text}'
    )
