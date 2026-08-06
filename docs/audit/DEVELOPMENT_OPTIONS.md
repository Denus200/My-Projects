# Варианты дальнейшего развития

## Готовность к запрошенному развитию

| Направление | Оценка | Основание |
|---|---|---|
| Новый Bento Dashboard | **Requires refactoring** | Есть только один `content_area` и монолитный Today view; dashboard read models/components отсутствуют. [`main.py`](../../main.py), строки 26–46; [`ui/views/home.py`](../../ui/views/home.py) |
| Единая сущность Task | **Possible with minor changes** для текущего MVP, **Requires refactoring** для полного roadmap | Канонические Task dataclass/table/repository уже есть, но API ограничен Today, нет relations/migrations. [`core/models.py`](../../core/models.py), строки 14–26; [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py) |
| Projects | **Requires refactoring** | Модель/create/list готовы, но нет CRUD-экрана и UI практически не создаёт второй проект. [`core/models.py`](../../core/models.py), строки 4–11; [`ui/views/home.py`](../../ui/views/home.py), строки 42–49 и 152–168 |
| 12-Week Cycles | **Requires refactoring** | Сущность/таблица отсутствует; нужны migrations, связи и use cases. [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md#запрошенные-сущности-которых-нет) |
| Weekly Progress | **Requires refactoring** | Доступна только выборка одной даты с `LIMIT 3`; нет completion history/read model. [`storage/repositories/task_repository.py`](../../storage/repositories/task_repository.py), строки 67–79 |
| Work Sessions | **Requires refactoring** | Сущность и timer/background lifecycle отсутствуют; одно SQLite connection не имеет фонового контракта. [`main.py`](../../main.py), строки 13–19; [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md#ошибки-фоновые-процессы-и-асинхронность) |
| Централизованные design tokens | **Possible with minor changes** | Палитра и radius уже централизованы; нужно добавить typography/spacing и убрать direct colors. [STYLES_AUDIT.md](STYLES_AUDIT.md#готовность-к-design-tokens) |
| Settings | **Requires refactoring** | Есть только disabled-кнопка; модели, хранения и экрана нет. [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 27–31 |
| Лёгкий desktop-widget | **Requires refactoring** | Core services можно сохранить, но нужен отдельный entry point/read model, lifecycle и connection ownership; текущий `main.py` строит всё окно целиком. [`main.py`](../../main.py), строки 13–50 |
| SQLite и миграции | **Requires refactoring** | SQLite уже централизована и цела, но `user_version=0`, runner/backup отсутствуют. [`storage/database.py`](../../storage/database.py), строки 17–47; D2 |
| Новые модули в будущем | **Requires refactoring** | Ручная composition допустима для двух сервисов, но строковая навигация и closure state не масштабируются. [`main.py`](../../main.py), строки 26–36; [`ui/views/home.py`](../../ui/views/home.py) |

Ни один отсутствующий модуль не оценён как «Better to rebuild this module», потому что фактического модуля ещё нет. Неподключённый File tools — исключение: его безопаснее считать прототипом и заново спроектировать execution часть, сохранив только полезные визуальные идеи. Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 54–64.

## Стратегия 1 — продолжать текущую архитектуру без реорганизации

### Что сохраняется

Весь код, текущая SQLite-схема, Today UI, ручные services/repositories и быстрый локальный темп изменений. Основание: небольшое дерево из 877 строк Python в [PROJECT_TREE.md](PROJECT_TREE.md).

### Что придётся изменить

Каждую новую сущность добавлять напрямую в `storage/database.py`, создавать repository/service, расширять строковый `navigate` и увеличивать views. Bento widgets будут напрямую вызывать новые сервисы по текущему образцу [`main.py`](../../main.py), строки 13–36.

### Риски

- схема расходится между существующими БД;
- `main.py` превращается в ручной реестр всего приложения;
- UI state/refetch логика дублируется;
- новые entry points повторяют или обходят UI-only validation;
- невозможно безопасно развивать background/widget поверх одного connection.

Основание: High/Medium пункты в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md).

### Сложность и новые проблемы

Начальная сложность низкая, но вероятность новых проблем **высокая**: H2/H3/H4 уже показывают, что простые локальные решения имеют глобальные эффекты для данных.

### Вывод

Пригодно только для короткой стабилизации текущего MVP, не для заявленного roadmap.

## Стратегия 2 — постепенно реорганизовать существующий проект

### Что сохраняется

- рабочий файл SQLite и его данные;
- dataclass Project/Task и status values как совместимый baseline;
- параметризованные SQL repositories;
- проверенные Project/Today services;
- Today UI как characterization target;
- 8 существующих тестов.

Основание: успешные D2–D4 в [CURRENT_STATE.md](CURRENT_STATE.md#диагностика).

### Что меняется

Последовательно, небольшими проверяемыми шагами:

1. воспроизводимое окружение и safety net;
2. migration/backup layer вокруг текущей схемы;
3. unit-of-work и domain validation;
4. application queries/commands, не привязанные к Flet controls;
5. navigation registry/app shell;
6. component/design-token layer;
7. новые модули по одному вертикальному срезу.

Подробная последовательность: [NEXT_STEPS.md](NEXT_STEPS.md).

### Риски

- временно сосуществуют старый и новый patterns;
- требуется дисциплина совместимости migrations;
- UI decomposition может дать визуальные регрессии.

### Сложность и новые проблемы

Сложность **средняя**, вероятность новых проблем **низкая–средняя**, если каждый шаг закреплён characterization/migration tests и не объединён с новой функциональностью.

### Вывод

**Рекомендуемый вариант.** Он сохраняет реально работающие слои и данные, но сначала устраняет общий риск schema evolution. Объём текущего кода невелик, поэтому границы можно ввести постепенно без длительной двойной системы.

## Стратегия 3 — новый чистый фундамент с переносом работающих частей

### Что сохраняется

Можно перенести domain values, Project/Task semantics, SQL данные через migration/importer, визуальную палитру и поведенческие тесты. Нельзя считать текущий UI и repository API автоматически совместимыми.

### Что придётся изменить

Новая package structure, app shell/navigation, migration system, data access contract, UI components и отдельный compatibility importer/validator для `overlord.db`. Today flow придётся реализовать заново и сравнить с D4/тестами.

### Риски

- двойная разработка и длительный период без feature progress;
- незамеченная потеря edge cases/данных при переносе;
- необходимость поддерживать старую и новую БД/приложение до cutover;
- новый фундамент может повторить неопределённые product decisions (Cycles, Blockers, Sessions ещё не смоделированы).

### Сложность и новые проблемы

Сложность **высокая**, вероятность новых проблем **средняя–высокая**. Чистота структуры сама по себе не компенсирует migration/cutover risk.

### Когда оправдано

Только если до начала реализации появятся несовместимые требования к GUI/runtime/storage, которые нельзя ввести миграциями, либо если экспериментальный File tools станет отдельным продуктом. Текущие доказательства этого не показывают.

## Рекомендация

Выбрать **стратегию 2: постепенная реорганизация существующего проекта**. Не продолжать прямое наращивание экранов до baseline migration и safety tests, но и не делать полный rewrite: текущие SQLite, repositories, services, Today flow и тесты работоспособны и достаточно малы для контролируемого улучшения. Главный критерий решения — сохранность пользовательских данных, а не эстетика структуры. Основание: целостность D2, работоспособность D3/D4 и главный риск в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md#главный-архитектурный-риск).
