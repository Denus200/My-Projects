# Следующие шаги

Это только план; реализация в рамках аудита не выполнялась.

## Фаза 0 — зафиксировать baseline

1. Инициализировать version control и сделать первый осмысленный snapshot исходников, отдельно решив судьбу `.venv`, `__pycache__` и рабочей БД. Не удалять `data/overlord.db` без проверенного backup. Основание: [PROJECT_TREE.md](PROJECT_TREE.md#генерируемые-и-локальные-файлы).
2. Зафиксировать Python/Flet/direct dependencies в manifest + lock и документировать команды setup/run/test. Основание: H1 в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md#h1-окружение-и-сборка-невоспроизводимы).
3. Сохранить диагностический baseline: 8/8 тестов, окно 1280×720, текущая схема/row counts/hash по [CURRENT_STATE.md](CURRENT_STATE.md#диагностика).
4. Добавить characterization tests для известных границ: второй Project, четвёртая Task, invalid minutes через service, compound create failure, nonexistent Task update и database-open failure. Основание: H3–H6 и M7.

Критерий завершения: чистое окружение воспроизводит запуск и тесты по документации; текущая БД открывается без преобразования.

## Фаза 1 — безопасность данных и миграции

1. Описать текущую DDL как schema baseline version 1 без изменения существующих значений.
2. Спроектировать migration runner с последовательными версиями, транзакцией, pre-migration backup и проверкой integrity/FK до и после.
3. Проверить три сценария на копиях: новая пустая БД, текущая `user_version=0` БД, повторный запуск уже мигрированной БД.
4. Добавить documented recovery: где backup, как перейти в read-only и как восстановиться после неуспеха.

Основание: H2 и главный риск в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md#главный-архитектурный-риск).

Критерий завершения: migration tests доказывают сохранение Project/Task rows и повторяемость; production file не изменяется без backup.

## Фаза 2 — стабилизировать существующие сценарии

1. Сделать compound «Project + first Task» одной валидируемой транзакцией.
2. Разделить UI flows выбора существующего и создания нового Project.
3. Формально решить контракт 1–3 focus tasks: hard limit или отдельный focus selection; устранить невидимую четвёртую запись.
4. Перенести minutes/status/date invariants из Flet UI в application/domain layer и согласовать DB constraints через migration.
5. Добавить startup/database error boundary, понятные сообщения и минимальный local log.
6. Закрывать connections при завершении session/window.
7. После фиксации Flet версии заменить deprecated `ft.app` на поддерживаемый startup API и повторить GUI smoke.

Основание: H3–H6, M2, M6 и L5 в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md).

Критерий завершения: все новые regression tests проходят; ни один error path не оставляет частичный Project/Task; startup failure не портит БД.

## Фаза 3 — application boundaries и shell

1. Ввести явные commands/queries или use-case services для Project/Task без зависимости от Flet controls.
2. Определить unit-of-work/connection factory, пригодную для UI и будущего widget/background work.
3. Разделить `home.py` на view composition, небольшие компоненты и testable presentation state.
4. Заменить строковый `if home` на registry/router с not-found handling и выбранным navigation state.
5. Сохранить текущий Today как первый вертикальный срез; не добавлять несколько новых модулей одновременно.

Основание: M1, M3, M5 и фактическая архитектура в [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md).

Критерий завершения: Today работает через новый boundary, а repositories не импортируются UI-слоем напрямую/через composition вне утверждённого root.

## Фаза 4 — design system до Bento-масштабирования

1. Расширить `AppStyle` semantic tokens: backgrounds/surfaces/text/states, typography scale, spacing scale, radii и component sizes.
2. Убрать direct `white/red*/transparent` из будущих подключаемых экранов.
3. Определить dark/light variants или явно зафиксировать dark-only product decision.
4. Создать небольшой набор повторно используемых Bento card/form/navigation components.
5. Выполнить визуальные smoke tests на минимальном и обычном размере окна.

Основание: [STYLES_AUDIT.md](STYLES_AUDIT.md).

Критерий завершения: палитра/spacing/typography меняются централизованно; Today визуально не регрессировал.

## Фаза 5 — новые data-модули по порядку зависимостей

Рекомендуемый порядок, каждый пункт — отдельная migration + domain/use-case/UI/test slice:

1. **Projects**: полноценный list/create/edit/archive, потому что Task уже зависит от Project.
2. **Unified Task semantics**: стабильные поля, ordering/focus, transitions и query API.
3. **12-Week Cycles + Milestones**: связи с Project/Task и границы дат.
4. **Weekly Progress/Review**: read model поверх завершённых Task/Cycle данных, а не новый источник истины.
5. **Work Sessions**: отдельная сущность и connection/background lifecycle.
6. **Blocker details**: решить, это entity/event или расширение Task; не ограничиваться строкой `blocked`.
7. **Settings**: schema/typed settings, затем UI; не хранить произвольные значения без versioning.
8. **Bento Dashboard**: композиция готовых read models; dashboard не должен владеть бизнес-логикой.
9. **Desktop widget**: отдельный лёгкий entry point, использующий те же queries, но собственную session/connection.

Основание отсутствия сущностей: [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md#запрошенные-сущности-которых-нет); readiness: [DEVELOPMENT_OPTIONS.md](DEVELOPMENT_OPTIONS.md#готовность-к-запрошенному-развитию).

## Фаза 6 — решение по File tools и сборке

1. Не подключать текущий `file_manager.py` как рабочий destructive tool.
2. Если функция нужна продукту, сначала определить безопасный plan/preview/confirm/execute/undo-or-report contract и filesystem tests на temp directories.
3. Только после стабилизации runtime создать документированную desktop build pipeline и smoke-test артефакта на чистой машине.

Основание: M8 и H1 в [RISKS_AND_TECH_DEBT.md](RISKS_AND_TECH_DEBT.md).

## Первые три действия

1. **Зафиксировать воспроизводимый baseline и regression tests** — иначе нельзя отделить рефакторинг от смены Flet/окружения.
2. **Ввести backup-tested schema version/migration baseline** — это защищает единственный пользовательский asset перед добавлением сущностей.
3. **Исправить атомарность Project+Task и контракт 1–3 задач, затем разделить Project flows** — это устраняет уже существующие data/UI ловушки до Bento и Cycles.

Эти действия следуют из H1–H5 и не требуют полного rewrite.
