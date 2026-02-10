"""Валидация данных пользователя."""


def validate_name(name: str) -> tuple[bool, str]:
    """Проверить корректность имени.

    Возвращает (is_valid, error_message).
    """
    name = name.strip()
    if len(name) < 2:
        return False, '❌ Имя должно содержать минимум 2 символа'
    if len(name) > 100:
        return False, '❌ Имя слишком длинное'
    return True, ''


def validate_age(age_text: str) -> tuple[bool, str, int]:
    """Проверить корректность возраста.

    Возвращает (is_valid, error_message, age_value).
    """
    try:
        age = int(age_text.strip())
    except ValueError:
        return False, '❌ Пожалуйста, введите корректный возраст (число от 14 до 100)', 0

    if age < 14 or age > 100:
        return False, '❌ Пожалуйста, введите корректный возраст (число от 14 до 100)', 0

    return True, '', age
