"""FSM состояния для бота."""

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    """Состояния регистрации пользователя."""
    waiting_for_phone = State()      # ожидание номера телефона
    waiting_for_name = State()       # ожидание имени
    waiting_for_age = State()        # ожидание возраста
    waiting_for_education = State()  # ожидание выбора образования


class Testing(StatesGroup):
    """Состояния прохождения тестирования."""
    answering = State()  # процесс ответа на вопросы


class AdminPanel(StatesGroup):
    """Состояния административной панели."""
    main_menu = State()           # главное меню админки
    questions_list = State()      # список вопросов
    adding_question_text = State()     # ввод текста нового вопроса
    adding_question_type = State()     # выбор типа вопроса
    adding_question_options = State()  # ввод вариантов ответа
    editing_question = State()         # редактирование вопроса
    editing_question_text = State()    # изменение текста вопроса
    editing_question_type = State()    # изменение типа вопроса
    editing_question_options = State() # изменение вариантов ответа
    confirm_delete = State()           # подтверждение удаления
