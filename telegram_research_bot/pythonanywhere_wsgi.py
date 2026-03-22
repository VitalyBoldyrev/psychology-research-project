"""Шаблон WSGI-файла для PythonAnywhere.

Скопируй содержимое этого файла в WSGI configuration file
на PythonAnywhere (вкладка Web → WSGI configuration file).
Замени USERNAME на свой логин PythonAnywhere.
"""

import sys

# Путь к проекту
project_path = '/home/USERNAME/telegram_research_bot/telegram_research_bot'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Путь к virtualenv (PythonAnywhere создаёт его автоматически)
# virtualenv_path = '/home/USERNAME/.virtualenvs/bot-venv'

from webapp import app as application  # noqa: E402
