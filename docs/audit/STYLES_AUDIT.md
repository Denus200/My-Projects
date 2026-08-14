# Аудит системы стилей

## Итог

Активный экран использует централизованную тёмную палитру, но полноценной системы design tokens нет. Цвета в основном вынесены, тогда как spacing, размеры компонентов, значительная часть типографики и несколько цветов остаются hardcoded. Светлая тема отсутствует. Основание: [`ui/style/theme.py`](../../ui/style/theme.py); [`main.py`](../../main.py), строки 21–24; перечисление hardcoded ниже.

## Централизованные значения

`AppStyle` определяет:

| Token | Значение | Использование |
|---|---:|---|
| `BG_MAIN` | `#1E1E2E` | фон Page, карточки input внутри task |
| `BG_SIDEBAR` | `#181825` | sidebar, поля, task/empty cards |
| `SURFACE` | `#313244` | форма добавления задачи |
| `PRIMARY` | `#89B4FA` | заголовки, активные иконки, borders |
| `SUCCESS` | `#A6E3A1` | сообщения об успехе |
| `WARNING` | `#F9E2AF` | feedback по умолчанию |
| `DANGER` | `#F38BA8` | validation errors |
| `TEXT_MAIN` | `#CDD6F4` | основной текст |
| `TEXT_MUTED` | `#6C7086` | вторичный текст/disabled визуал |
| `TITLE_SIZE` | `28` | заголовки экранов |
| `TEXT_SIZE` | `14` | определён, но не используется |
| `RADIUS` | `10` | большинство карточек |

Основание: [`ui/style/theme.py`](../../ui/style/theme.py), строки 1–14; поиск `AppStyle.` по `ui/**/*.py`.

## Темы

- Приложение принудительно ставит `ft.ThemeMode.DARK`; light mode и переключение темы отсутствуют. Основание: [`main.py`](../../main.py), строка 24.
- Отдельных Flet `Theme`, `ColorScheme`, font family или themed variants нет. Основание: [`main.py`](../../main.py), строки 21–24, и отсутствие других theme-конфигураций.
- Палитру активного Today можно в основном изменить в одном файле, но весь проект — нельзя: `file_manager.py` использует прямые Flet color strings. Основание: hardcoded colors ниже.

## Типографика

Централизован только `TITLE_SIZE=28`; `TEXT_SIZE=14` не используется. В коде напрямую встречаются размеры 12, 13, 18, 24, 30 и 34, а `weight="bold"` задаётся в отдельных контролах. Font family, line height и шкала типографики не заданы. Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 8–14; [`ui/views/home.py`](../../ui/views/home.py), строки 10–36, 63–149 и 178–225; [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 26–130.

## Spacing, размеры, радиусы и тени

- Spacing/padding hardcoded: `0, 4, 8, 10, 12, 15, 16, 18, 20, 24, 30, 36, 40` и другие значения. Единой шкалы нет. Основание: файлы в списке ниже.
- Фиксированные widths: sidebar 250, dropdown/input 260, minutes 90, status 170, file range 120. Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строка 8; [`ui/views/home.py`](../../ui/views/home.py), строки 13–36 и 84–101; [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 37–41.
- Централизован только `RADIUS=10`; тени не заданы нигде. Основание: [`ui/style/theme.py`](../../ui/style/theme.py), строка 14; отсутствие `shadow=` по `ui/**/*.py`.
- У layout нет централизованных breakpoints/min window sizes. В нескольких местах используется `wrap`/`expand`, но фиксированные widths остаются. Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 178–225.

## Файлы с hardcoded визуальными значениями

### `ui/style/theme.py`

Централизованный источник содержит 9 HEX-цветов и три числовых token. Это намеренные tokens, но их структура не разделяет semantic/component tokens и не поддерживает темы. Основание: [`ui/style/theme.py`](../../ui/style/theme.py), строки 1–14.

### `main.py`

- `page.padding = 0`;
- принудительный `ThemeMode.DARK`;
- row `spacing=0`.

Основание: [`main.py`](../../main.py), строки 21–24 и 38–43.

### `ui/components/sidebar.py`

- width 250, padding 20;
- brand text size 24 и hardcoded `bold`;
- divider height 30.

Основание: [`ui/components/sidebar.py`](../../ui/components/sidebar.py), строки 6–35.

### `ui/views/home.py`

- widths 260, 90, 170;
- font sizes 12, 13, 18, 34;
- paddings 16, 18, 24, 36;
- spacings 4, 8, 12, 18;
- hardcoded weights `bold`;
- layout/alignment задаются локально.

Основание: [`ui/views/home.py`](../../ui/views/home.py), строки 9–225.

### `ui/views/file_manager.py`

- прямые цвета `"white"`, `"red600"`, `"red400"`, `"transparent"`;
- widths 120, heights 10/30/150/250;
- paddings 15/20/40;
- icon size 30 и hardcoded `bold`.

Основание: [`ui/views/file_manager.py`](../../ui/views/file_manager.py), строки 26–130.

## Дублирование

Цвета активного Today в основном не дублируются как literals благодаря `AppStyle`. Однако одни и те же числовые значения (`12`, `18`, `20`, `30`) повторяются в разных семантических ролях, а `file_manager.py` обходит token `DANGER` прямыми `red400/red600`. Поэтому централизованная смена цветовой палитры неполна, а смена spacing/typography требует редактировать несколько файлов. Основание: результаты `rg` по `AppStyle`, `padding|spacing|size|width|height|color` от 2026-08-06.

## Готовность к design tokens

Оценка: **Possible with minor changes** для существующего Today UI. Уже есть единая точка цветов и базовый радиус; потребуется расширить её semantic tokens для typography/spacing/sizes, убрать прямые цвета из `file_manager.py` и передавать theme variant вместо жёсткого `DARK`. Для полноценного Bento Dashboard это должно предшествовать массовому созданию компонентов, иначе hardcoded-значения размножатся. Основание: [`ui/style/theme.py`](../../ui/style/theme.py) и список hardcoded-файлов выше.
