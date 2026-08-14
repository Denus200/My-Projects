# Дерево проекта Overlord

Дата снимка: 2026-08-06. Корень проекта: `E:\Projects\Overlord`.

## Фактическая структура

```text
Overlord/
├── .venv/                         # Локальное Python-окружение, 7 880 файлов, ~61,6 МБ
├── assets/
│   ├── icons/                     # Пусто
│   └── images/                    # Пусто
├── core/
│   ├── __init__.py                # Пустой маркер пакета
│   ├── models.py                  # Dataclass-модели Project и Task
│   ├── statuses.py                # TaskStatus и функции валидации статуса
│   └── __pycache__/               # Сгенерированный bytecode
├── data/
│   ├── overlord.db                # Рабочая SQLite БД, 24 576 байт
│   └── test-tmp/                  # Корень временных БД тестов; после аудита пуст
├── docs/
│   └── audit/                     # Семь отчётов текущего аудита
├── services/
│   ├── __init__.py                # Пустой маркер пакета
│   ├── project_service.py         # Валидация создания и чтение активных проектов
│   ├── today_service.py           # Сценарии задач на сегодня и смены статуса
│   └── __pycache__/               # Сгенерированный bytecode
├── storage/
│   ├── __init__.py                # Пустой маркер пакета
│   ├── database.py                # Путь к БД, соединение и начальная DDL-схема
│   ├── repositories/
│   │   ├── __init__.py            # Пустой маркер пакета
│   │   ├── project_repository.py  # SQL для Project
│   │   ├── task_repository.py     # SQL для Task
│   │   └── __pycache__/           # Сгенерированный bytecode
│   └── __pycache__/               # Сгенерированный bytecode
├── tests/
│   ├── test_daily_focus_services.py # 7 сервисных/SQLite тестов
│   ├── test_startup_ui.py           # 1 AST-проверка стартового UI
│   └── __pycache__/                 # Сгенерированный bytecode
├── ui/
│   ├── components/
│   │   ├── sidebar.py             # Боковая навигация
│   │   └── __pycache__/
│   ├── style/
│   │   ├── theme.py               # Частичный набор design tokens
│   │   └── __pycache__/
│   └── views/
│       ├── home.py                # Единственный подключённый экран Today
│       ├── file_manager.py        # Неподключённый прототип File tools
│       └── __pycache__/
├── __pycache__/                   # Сгенерированный bytecode main.py
├── main.py                        # Точка входа и composition root
└── requirements.txt               # Пустой файл зависимостей
```

Основание: результат `rg --files -g '!**/.git/**'`, рекурсивный `Get-ChildItem` и подсчёт файлов по каталогам от 2026-08-06. В проекте 877 строк Python, включая 131 строку тестов; пофайловый подсчёт выполнен через `Get-Content -Encoding UTF8`.

## Важные отсутствующие элементы

- `AGENTS.md` не найден ни в `E:\Projects`, ни в проекте. Основание: `rg --files -g 'AGENTS.md' E:\Projects` не вернул путей.
- README и другая исходная документация отсутствовали до аудита. Основание: рекурсивный поиск `README*` и `*.md` не вернул файлов.
- Git-репозитория нет: `git status --short --branch` из корня завершился сообщением `fatal: not a git repository`.
- Конфигурации сборки нет: не найдены `pyproject.toml`, `setup.py`, `setup.cfg`, `*.spec`, `Pipfile`, lock-файлы, `Dockerfile`, `Makefile`, YAML/TOML/JSON/INI-конфиги. Основание: рекурсивный поиск кандидатов, исключая `.venv` и кэши.
- `.gitignore` отсутствует; `.venv` и многочисленные `__pycache__` находятся прямо внутри дерева проекта. Основание: верхнеуровневый `Get-ChildItem -Force` и список `rg --files`.

## Назначение верхнеуровневых частей

| Путь | Фактическая роль | Доказательство |
|---|---|---|
| `main.py` | Создаёт соединение, репозитории, сервисы, каркас окна и открывает `home` | [`main.py`](../../main.py), строки 13–50 |
| `core/` | Две неизменяемые dataclass-модели и enum статусов задач | [`core/models.py`](../../core/models.py), строки 4–26; [`core/statuses.py`](../../core/statuses.py), строки 4–18 |
| `services/` | Тонкая прикладная валидация и координация репозиториев | [`services/project_service.py`](../../services/project_service.py), строки 4–15; [`services/today_service.py`](../../services/today_service.py), строки 8–41 |
| `storage/` | SQLite-соединение, DDL и ручные SQL-репозитории | [`storage/database.py`](../../storage/database.py), строки 5–47; [`storage/repositories/`](../../storage/repositories/) |
| `ui/` | Flet-компоненты, экран Today, неподключённый прототип File tools и частичная тема | [`ui/`](../../ui/) |
| `tests/` | Сервисные интеграционные тесты с временной SQLite и одна статическая AST-проверка | [`tests/test_daily_focus_services.py`](../../tests/test_daily_focus_services.py), строки 15–110; [`tests/test_startup_ui.py`](../../tests/test_startup_ui.py), строки 6–21 |
| `data/overlord.db` | Единственное постоянное хранилище пользовательских данных | [`storage/database.py`](../../storage/database.py), строка 5; диагностическая схема в [CURRENT_STATE.md](CURRENT_STATE.md#диагностика) |
| `assets/` | Зарезервированные, но пустые каталоги | Диагностика `Get-ChildItem assets -Recurse` |

## Генерируемые и локальные файлы

`.venv/` содержит установленный Flet, PyInstaller и транзитивные зависимости, но не является декларацией зависимостей. `__pycache__/` содержит варианты `.pyc`, в том числе файлы с числовыми суффиксами. Эти каталоги не используются как исходный контракт проекта; без Git невозможно установить, какие из них намеренно сохранялись. Основание: `.venv` содержит 7 880 файлов, а [`requirements.txt`](../../requirements.txt) имеет размер 0 байт.
