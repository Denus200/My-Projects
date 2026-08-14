# Текущее состояние Overlord

Дата проверки: 2026-08-06, Windows 10. Все действия были диагностическими; производственный код не изменялся.

## Стек и запуск

| Параметр | Фактическое состояние | Доказательство |
|---|---|---|
| Python | 3.14.3, системный и `.venv` | Диагностика D1 |
| GUI | Flet 0.84.0 (`flet`, `flet-cli`, `flet-desktop`) | Диагностика D1; [`main.py`](../../main.py), строка 1 |
| База | SQLite 3.50.4, файл `data/overlord.db` | Диагностика D2; [`storage/database.py`](../../storage/database.py), строки 5–14 |
| Точка входа | `main.py` | [`main.py`](../../main.py), строки 13–50 |
| Штатная команда | `.venv\Scripts\python.exe main.py` из корня проекта | Успешный запуск D4; guard в [`main.py`](../../main.py), строки 49–50 |
| Зависимости | В `.venv` установлено 37 пакетов; `requirements.txt` пуст | Диагностика D1; [`requirements.txt`](../../requirements.txt) |
| Сборка | Unknown: в проекте нет конфигурации или документированной команды сборки | Диагностика D1 и дерево в [PROJECT_TREE.md](PROJECT_TREE.md#важные-отсутствующие-элементы) |

Наличие `pyinstaller==6.19.0` и `flet-cli==0.84.0` только в локальной `.venv` не доказывает существующий процесс сборки: spec/manifest/CI/README отсутствуют.

## Используемые библиотеки

- Единственная сторонняя runtime-зависимость, непосредственно импортируемая исходным кодом, — `flet`. Основание: импорты [`main.py`](../../main.py), [`ui/components/sidebar.py`](../../ui/components/sidebar.py), [`ui/views/home.py`](../../ui/views/home.py), [`ui/views/file_manager.py`](../../ui/views/file_manager.py).
- Runtime standard library: `sqlite3`, `pathlib`, `dataclasses`, `enum`, `datetime`. Основание: импорты в [`storage/database.py`](../../storage/database.py), [`core/models.py`](../../core/models.py), [`core/statuses.py`](../../core/statuses.py), [`services/today_service.py`](../../services/today_service.py) и repositories.
- Tests используют `unittest`, `tempfile`, `os`, `ast`, `pathlib`, `datetime`. Основание: [`tests/test_daily_focus_services.py`](../../tests/test_daily_focus_services.py), строки 1–12; [`tests/test_startup_ui.py`](../../tests/test_startup_ui.py), строки 1–3.
- Остальные 30+ пакетов из `.venv` являются инструментами или транзитивными зависимостями; по исходникам нельзя доказать, какие из них должны быть прямыми production dependencies. Основание: D1 и поиск всех `import` по `*.py`.

## Настройки и конфигурация

Отдельных конфигурационных файлов нет. Фактические настройки жёстко находятся в коде: путь к БД — [`storage/database.py`](../../storage/database.py), строка 5; title/background/padding/dark mode — [`main.py`](../../main.py), строки 21–24; визуальные constants — [`ui/style/theme.py`](../../ui/style/theme.py). Переменные окружения, пользовательский Settings store и feature flags не читаются. Основание: дерево/поиск конфигов в [PROJECT_TREE.md](PROJECT_TREE.md#важные-отсутствующие-элементы) и полный список импортов.

## Реально доступный интерфейс

Приложение открывает одно отвечающее окно `Overlord` размером 1280×720 и сразу показывает экран `Today`. На нём есть:

- dropdown активного проекта;
- поле `New project`;
- поля названия задачи и плановых минут;
- кнопка добавления;
- до трёх карточек задач на текущую локальную дату либо пустое состояние;
- для каждой видимой задачи — статус, комментарий и сохранение.

Основание: визуальная диагностика D4; создание контролов в [`ui/views/home.py`](../../ui/views/home.py), строки 9–225.

Навигация фактически состоит из одного активного пункта `Today`. `File tools` и `Settings` отображаются, но имеют `disabled=True`; обработчик навигации умеет построить только `home`. Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 15–32; [`main.py`](../../main.py), строки 28–34.

Файл [`ui/views/file_manager.py`](../../ui/views/file_manager.py) не импортируется из `main.py`, не имеет маршрута и потому не является доступным экраном. Внутри это прототип: preview меняет только текст, а `execute_btn` не имеет `on_click`. Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 54–64; импорты [`main.py`](../../main.py), строки 8–10.

## Что работает

- Приложение запускается в текущей `.venv`, создаёт/проверяет таблицы и рендерит `Today`. Основание: D4; [`main.py`](../../main.py), строки 13–50.
- Создание Project и Task, выборка сегодняшних задач, ограничение выдачи тремя задачами, смена статуса/комментария и проверка внешнего ключа работают на временной SQLite. Основание: D3 — 8/8 тестов успешно; [`tests/test_daily_focus_services.py`](../../tests/test_daily_focus_services.py), строки 30–106.
- Персистентность после закрытия и повторного открытия соединения доказана тестом. Основание: [`tests/test_daily_focus_services.py`](../../tests/test_daily_focus_services.py), строки 89–106; D3.
- Рабочая БД целостна: `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check = []`, сиротских задач 0. Основание: D2.
- Путь к БД вычисляется от расположения модуля, а не от текущей рабочей папки. Основание: [`storage/database.py`](../../storage/database.py), строка 5.
- Все модули приложения, включая неподключённый `file_manager`, импортируются без ошибки под текущим окружением. Основание: D5.

## Что не реализовано или является заглушкой

- Других подключённых экранов, кроме `Today`, нет. Основание: [`main.py`](../../main.py), строки 28–34.
- `File tools` и `Settings` отключены. Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 21–31.
- Исполнение файловых операций отсутствует; доступен только генератор текстового preview в неподключённом модуле. Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 55–64.
- Нет UI для списка/редактирования/архивации проектов, исторических или будущих задач, циклов, milestones, weekly review, sessions и настроек. Основание: полный список исходных файлов в [PROJECT_TREE.md](PROJECT_TREE.md#фактическая-структура) и единственный маршрут в [`main.py`](../../main.py), строки 28–34.
- Нет светлой темы: окно принудительно использует `ThemeMode.DARK`. Основание: [`main.py`](../../main.py), строка 24.
- Нет сборочной команды, миграций, логирования, backup/restore и документации запуска. Основание: [PROJECT_TREE.md](PROJECT_TREE.md#важные-отсутствующие-элементы); [`storage/database.py`](../../storage/database.py), строки 17–47.

## Наблюдаемые UI-проблемы

1. Одновременно показаны предвыбранный Project и `New project`, но при наличии выбранного проекта введённый новый заголовок игнорируется. Основание: автоселект в [`ui/views/home.py`](../../ui/views/home.py), строки 42–49, и ветка создания только при `project_id is None`, строки 152–168.
2. Четвёртую и последующие задачи UI позволяет сохранить, но `Today` всегда читает только первые три по времени создания; новая задача становится невидимой. Основание: [`services/today_service.py`](../../services/today_service.py), строки 13–14; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 67–79; тест намеренно закрепляет лимит в [`tests/test_daily_focus_services.py`](../../tests/test_daily_focus_services.py), строки 46–54.
3. Пустое состояние занимает фиксированную узкую карточку в большой рабочей области; адаптивность окна и минимальные размеры не настроены. Основание: визуальная диагностика D4 и фиксированные размеры в [`ui/views/home.py`](../../ui/views/home.py), строки 13–36 и 63–81.
4. Активный экран англоязычный, прототип File tools — украиноязычный; единой локализации нет. Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 14–36 и 191–195; [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 7–44.

## Данные рабочей БД

На момент аудита схема содержит только таблицы `projects` и `tasks` и два индекса. В базе 1 активный проект и 2 задачи со статусом `planned`; даты задач лежат в диапазоне 2026-05-11…2026-06-13, задач на 2026-08-06 нет. Хеш файла до и после GUI-запуска совпал: `E8339C04B31A302BCEDE1E0A5C708B5A130FA2E368F3D868BBD4CA95A8EFE527`; размер и `LastWriteTimeUtc` также не изменились. Основание: D2 и D4.

## Известные ошибки и предупреждения

- Штатный запуск пишет `DeprecationWarning: app() is deprecated since version 0.80.0. Use run() instead.` для [`main.py`](../../main.py), строки 49–50. Основание: stderr D4.
- Первый тестовый прогон внутри управляемой файловой песочницы дал 7 ошибок `sqlite3.OperationalError: unable to open database file`, потому что песочница запретила доступ к только что созданным каталогам `data/test-tmp/tmp*`. Повтор того же набора вне песочницы дал 8/8 OK; созданные первым прогоном временные каталоги удалены. Это ограничение среды аудита, а не воспроизводимый дефект Overlord. Основание: D3.
- Автоматизатор Windows Computer Use не смог запустить helper (`spawn EPERM`), поэтому окно было подтверждено через `Get-Process`, Win32 `PrintWindow` и визуальный снимок без кликов по данным. Основание: D4.

## Диагностика

### D1 — окружение и метаданные

Команды: `python --version`, `.venv\Scripts\python.exe --version`, `.venv\Scripts\python.exe -m pip list --format=freeze`, чтение Flet metadata, поиск build/config файлов. Результат: Python 3.14.3; Flet 0.84.0; конфигураций сборки нет; `requirements.txt` пуст.

### D2 — SQLite только для чтения

Соединение открывалось URI `mode=ro`; выполнены `PRAGMA integrity_check`, `foreign_key_check`, чтение `sqlite_master`, `table_info`, агрегаты и SHA-256. Результат: SQLite 3.50.4, integrity `ok`, FK-ошибок нет, `user_version=0`, journal mode `delete`, 1 Project, 2 Task.

### D3 — тесты

Команда: `.venv\Scripts\python.exe -m unittest discover -s tests -v`. Итог вне песочницы: `Ran 8 tests ... OK` (7 сервисных/SQLite и 1 AST UI test).

### D4 — реальный GUI-запуск

Команда: `.venv\Scripts\python.exe main.py`. Процессы Python и Flet оставались активными; окно `Overlord` отвечало, размер 1280×720, Win32 `PrintWindowSucceeded=True`. В stderr только deprecation warning. После корректного закрытия процессов не осталось, SHA-256 рабочей БД не изменился.

### D5 — import smoke test

Импортированы все модули `main`, `core`, `services`, `storage`, `ui`, включая `ui.views.file_manager`; результат `all application modules imported`. Проверено наличие Flet API: `app`, `run`, `FilePicker`, `Button`, `Tabs` — все доступны в 0.84.0.
