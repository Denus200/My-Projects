# Текущая архитектура Overlord

Это описание фиксирует фактическое устройство на 2026-08-06, без предложения новой модели.

## Общая форма

Проект имеет простую ручную слоистую структуру:

```text
Flet UI (main.py, ui/)
        ↓ прямые вызовы
Application services (services/)
        ↓ прямые вызовы
Repositories (storage/repositories/)
        ↓ sqlite3 SQL + commit
SQLite (data/overlord.db)
        ↑ новые запросы сервисов
Flet controls обновляются через page.update()
```

`main.py` выступает composition root: вручную создаёт одно соединение, два репозитория, два сервиса и передаёт сервисы в экран. Контейнера зависимостей, event bus, глобального store или ORM нет. Основание: [`main.py`](../../main.py), строки 13–46.

## Точка входа и инициализация

```text
python main.py
  → ft.app(main)
  → main(page)
  → connect_database(DEFAULT_DATABASE_PATH)
  → initialize_database(connection)
  → ProjectRepository + TaskRepository
  → ProjectService + TodayService
  → свойства Page
  → content_area + sidebar
  → page.add(Row(...))
  → navigate("home")
  → home_view(...)
  → load_projects() + refresh_tasks()
  → page.update()
```

Основание: [`main.py`](../../main.py), строки 13–50; синхронная начальная загрузка в [`ui/views/home.py`](../../ui/views/home.py), строки 175–176.

Соединение SQLite создаётся один раз на сессию приложения и не закрывается явным lifecycle hook. На старте всегда выполняется идемпотентный DDL `CREATE TABLE/INDEX IF NOT EXISTS`, затем `commit`. Основание: [`storage/database.py`](../../storage/database.py), строки 8–14 и 17–47; отсутствие close-кода в [`main.py`](../../main.py).

## Навигация

Навигация — локальная функция `navigate(view_name)` и строковый `if view_name == "home"`. Перед выбором она очищает `content_area.content`; для неизвестного имени останется пустая область. Истории, URL/routes, back stack, registry экранов и выбранного состояния sidebar нет. Основание: [`main.py`](../../main.py), строки 26–36.

Sidebar создаётся фабрикой и получает callback. Только `Today` вызывает `navigate_to("home")`; другие кнопки отключены. Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 6–35.

## Структура UI и состояние

Активный экран целиком строится функцией `home_view`. Все контролы и обработчики являются локальными переменными/closures:

- временное UI-состояние хранится в `value`, `options`, `controls`, `color` Flet-контролов;
- постоянное состояние хранится в SQLite;
- `load_projects()` вручную перечитывает dropdown;
- `refresh_tasks()` вручную очищает и заново создаёт карточки;
- после мутаций обработчики вызывают `page.update()`.

Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 9–176.

Отдельного state manager нет. Сервис не публикует события; UI сам решает, когда перечитать данные. `home_view` одновременно содержит layout, парсинг минут, выбор сценария создания Project/Task, обработку ошибок и перерисовку — 225 строк. Основание: [`ui/views/home.py`](../../ui/views/home.py).

## Фактические потоки данных

### Начальная загрузка

```text
UI home_view
  → ProjectService.list_active_projects()
  → ProjectRepository.list_by_status("active")
  → SQLite SELECT projects
  → dropdown.options/value

UI home_view
  → TodayService.get_today_tasks()
  → TaskRepository.list_for_date(date.today(), limit=3)
  → SQLite JOIN tasks/projects + LIMIT 3
  → новые task cards
  → page.update() вызывается navigate()
```

Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 42–49 и 63–84; [`services/project_service.py`](../../services/project_service.py), строки 14–15; [`services/today_service.py`](../../services/today_service.py), строки 13–14; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 67–79.

### Добавление задачи в выбранный проект

```text
Add icon
  → UI parse project id/title/minutes
  → TodayService.create_task()
  → ProjectRepository.get_by_id() (проверка FK на уровне сервиса)
  → TaskRepository.create()
  → INSERT tasks + commit
  → SELECT созданной Task с JOIN Project
  → UI очищает поля, reload projects, refresh tasks
  → page.update()
```

Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 152–173; [`services/today_service.py`](../../services/today_service.py), строки 16–36; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 31–65.

### Добавление новой Project вместе с Task

Реальный поток отличается от единой транзакции:

```text
Add icon при пустом project_dropdown
  → ProjectService.create_project()
  → ProjectRepository.create()
  → INSERT project + COMMIT                 # транзакция завершена
  → TodayService.create_task()
  → TaskRepository.create()
  → INSERT task + COMMIT                    # отдельная транзакция
```

Если валидация или вставка Task завершится ошибкой, Project уже сохранён. Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 152–163; [`storage/repositories/project_repository.py`](../../storage/repositories/project_repository.py), строки 21–33; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 31–53.

### Сохранение статуса и комментария

```text
Save icon в карточке
  → TodayService.update_task_state()
  → проверка значения TaskStatus
  → TaskRepository.update_state()
  → UPDATE + COMMIT
  → SELECT обновлённой Task
  → refresh_tasks() + page.update()
```

Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 84–150; [`services/today_service.py`](../../services/today_service.py), строки 38–41; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 81–94.

## Модели данных

### Project — существует

| Аспект | Фактическое состояние |
|---|---|
| Определение | Frozen dataclass [`core/models.py`](../../core/models.py), строки 4–11 |
| Поля | `id`, `title`, `description`, `status`, `created_at`, `updated_at` |
| Создание | UI [`ui/views/home.py`](../../ui/views/home.py), строки 152–158 → [`services/project_service.py`](../../services/project_service.py), строки 8–12 → repository |
| Чтение | `get_by_id`, `list_by_status` в [`storage/repositories/project_repository.py`](../../storage/repositories/project_repository.py), строки 35–47 |
| Изменение | Не реализовано; `updated_at` никогда не обновляется кодом |
| Сохранение | Таблица `projects` из [`storage/database.py`](../../storage/database.py), строки 20–27 |
| Связи | `Project 1 ← N Task`, FK `tasks.project_id`, `ON DELETE RESTRICT` |

### Task — существует

| Аспект | Фактическое состояние |
|---|---|
| Определение | Frozen dataclass [`core/models.py`](../../core/models.py), строки 14–26 |
| Поля | `id`, `project_id`, денормализованное read-поле `project_title`, `title`, `description`, `scheduled_date`, `planned_minutes`, `status`, `comment`, `created_at`, `updated_at` |
| Создание | UI [`ui/views/home.py`](../../ui/views/home.py), строки 152–163 → [`services/today_service.py`](../../services/today_service.py), строки 16–36 → repository |
| Чтение | `get_by_id`, `list_for_date` с JOIN Project в [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 55–79 |
| Изменение | Только `status`, `comment`, `updated_at` через `update_state`, строки 81–94 того же файла |
| Сохранение | Таблица `tasks` из [`storage/database.py`](../../storage/database.py), строки 29–41 |
| Связи | Обязательная ссылка на Project; других FK нет |

`scheduled_date`, `created_at`, `updated_at` представлены строками и в dataclass, и в SQLite. `Task.project_title` не является столбцом `tasks`: он добавляется JOIN-запросами. Основание: [`core/models.py`](../../core/models.py), строки 15–26; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 55–79.

### Запрошенные сущности, которых нет

| Сущность | Результат |
|---|---|
| Cycle | **Absent** — нет class/table/repository/service/UI |
| Milestone | **Absent** |
| Work Session | **Absent** |
| Weekly Review | **Absent** |
| Blocker | **Absent как сущность**; есть только строковый статус `blocked` у Task в [`core/statuses.py`](../../core/statuses.py), строка 9 |
| Settings | **Absent как модель/хранилище**; есть только disabled-кнопка в [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 27–31 |

Основание для `Absent`: полный список исходных файлов [PROJECT_TREE.md](PROJECT_TREE.md#фактическая-структура), DDL [`storage/database.py`](../../storage/database.py), строки 17–47, и поиск имён по всем `*.py`. Поля/точки create/read/update/save для отсутствующих сущностей — **Unknown**, потому что реализаций нет.

## Доступ к данным и файлам

Репозитории используют параметризованные SQL-запросы, что защищает текущие значения от SQL injection. Каждый write сразу вызывает `connection.commit()`. Основание: [`storage/repositories/project_repository.py`](../../storage/repositories/project_repository.py), строки 21–33; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 31–53 и 81–94.

SQLite `foreign_keys=ON` устанавливается для соединения, но schema version/migrations нет (`PRAGMA user_version=0` по D2). `initialize_database` умеет только создать отсутствующие объекты, но не изменить существующие. Основание: [`storage/database.py`](../../storage/database.py), строки 8–47.

Реальной работы с файловой системой в продукте нет. Неподключённый `file_manager_view` открывает directory picker и формирует только текст preview; создание, rename и delete не реализованы. Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 5–64.

## Стили

Часть цветов и три числовых значения вынесены в `AppStyle`; Flet Theme не настраивается, темы не переключаются, множество размеров/отступов остаётся внутри views/components. Полный разбор: [STYLES_AUDIT.md](STYLES_AUDIT.md).

## Ошибки, фоновые процессы и асинхронность

- Активный UI перехватывает только `ValueError` при add/save и выводит его в feedback. SQLite errors, startup errors и неожиданные exceptions не обрабатываются. Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 103–110 и 152–173; [`main.py`](../../main.py), строки 13–50.
- Логирования и crash report нет. Основание: отсутствие модуля/импортов logging во всём дереве [PROJECT_TREE.md](PROJECT_TREE.md).
- Threads, timers, task queue и фоновые workers не используются. Единственная `async def` — открытие directory picker в недоступном File tools. Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 14–31; поиск `async`, `thread`, `timer` по исходникам.
- SQLite-соединение создано с дефолтными настройками `sqlite3.connect`, то есть архитектура не определяет отдельные connections/transactions для будущих фоновых задач. Основание: [`storage/database.py`](../../storage/database.py), строки 8–14.
