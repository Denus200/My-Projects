# Overlord Design System — Light Foundation

Status: implemented baseline. The Python modules are authoritative; this document defines usage and governance.

## Single source of truth

- Semantic values and scales: `overlord/ui/design_system/tokens.py`
- Stateful Flet styles and theme composition: `overlord/ui/design_system/styles.py` and `themes.py`
- Reusable control constructors: `overlord/ui/components/controls.py`
- Lucide adapter and pinned assets: `overlord/ui/design_system/icons.py` and `assets.py`

Do not add a second generated design-system directory, page-level HEX colors, local button state maps, or duplicate field styling. Page code chooses a semantic component or token; it does not define a new visual language.

## Direction

The baseline is a warm, restrained, data-dense Windows productivity interface with Crimson Focus accents. It favors clear hierarchy and immediate affordance over decoration. The light theme is the redesign target; the existing dark mapping remains compatible and receives state parity, but is not considered visually final.

The automatic UI/UX Pro Max palette and landing-page style suggestions were intentionally not adopted. Approved product decisions and runtime evidence require Crimson Focus, Segoe UI, desktop density, a persistent sidebar, and low-motion interaction feedback.

## Foundations

### Color

Colors are semantic. Surfaces, text, borders, controls, interaction states, focus, scrims, and feedback each have named roles. Muted text is supporting metadata only; normal body copy uses the primary or secondary text role. Status meaning is never communicated by color alone.

### Typography

The application uses Segoe UI with a five-step scale: small metadata, body, emphasis, section title, and page display. Body text uses a consistent line-height token. Weight communicates hierarchy; arbitrary sizes and decorative typefaces are not introduced at page level.

### Spacing and geometry

Spacing follows a 4-pixel base scale. Normal controls are 40 pixels high, compact controls are 36 pixels, and large or isolated targets may use 44 pixels. Cards, fields, buttons, chips, and tables use named radius and padding tokens. Layout spacing comes from tokens; fixed widths are reserved for intentional desktop constraints.

### Motion

Micro-interactions use a 150-millisecond fast transition. Motion clarifies hover, press, selection, and focus without shifting layout bounds. When effective motion is disabled, transition duration is zero while visual state feedback remains intact.

## Components

### Buttons

Four variants are available: Primary, Secondary, Tertiary, and Danger. Every variant defines Default, Hovered, Pressed, Focused, and Disabled states. Primary is reserved for the main action in a local decision area. Secondary is a bordered alternative, Tertiary is a low-emphasis action, and Danger is reserved for destructive operations.

Clickable elements must look actionable before hover. Hover confirms interaction; it is not the only affordance. Focus uses a two-pixel semantic ring. Disabled controls change both visual emphasis and cursor.

### Inputs

`text_field` is the standard outlined and filled input. It supports normal, compact, multiline, numeric, read-only, disabled, helper, and error configurations through Flet parameters while retaining shared geometry and state styling. `search_field` is the search variation and adds the local Lucide search affordance.

Labels remain visible. Placeholder-only identification is not allowed. Errors belong to the affected field. Complex inputs should use persistent helper text.

### Selects

`select_field` is the single-select dropdown. It supports compact and searchable variations. The trigger shares input geometry, focus treatment, and padding. Menus use a bounded height, low elevation, semantic border, and consistent radius. Large option sets should use searchable mode.

### Checkboxes and choice chips

Checkboxes provide hover, press, focus, selected, and disabled treatments with semantic labels. `choice_chip` is the compact filter/segmented-choice primitive. An unselected chip has a visible surface and border before hover; a selected chip adds a stronger border, tinted surface, accent label, and checkmark so selection is not color-only.

### Tables

`data_table` is the baseline for structured desktop data. It defines a 40-pixel heading row, 44-pixel data rows, visible dividers, restrained header contrast, row hover, selected-row treatment, sortable-column support through Flet, and shared typography. Toolbar, filtering, pagination, resizing, and bulk actions remain page-level compositions until repeated patterns justify additional shared components.

### Sidebar

The persistent Sidebar uses the supplied Overlord SVG mark and real route-specific Lucide icons. It is 232 pixels wide when expanded and 56 pixels when collapsed. Expanded navigation rows are full-width and 48 pixels high; compact navigation targets are 44 by 44 pixels with an 8-pixel radius and 8-pixel vertical gap. The header and first navigation item are separated by 24 pixels.

Active navigation uses the primary crimson surface with white content. Default content uses the dedicated Sidebar foreground role with no fill border; hover and pressed states use the soft crimson interaction scale. Expanded rows use a native text-bearing tile with a 20-pixel icon and an explicit 8-pixel icon-to-label gap, so route names remain visible while the rail is open. The open/close transition lasts 420 milliseconds with an ease-in-out curve; only width is animated, so the content does not fade or flash. In expanded mode the 48-pixel collapse control sits beside the 48-pixel brand mark and has no default fill or outline. In compact mode the mark is 32 pixels and changes to the working expand control on hover. The custom language toggle uses a 56 by 32 pixel pill track and a circular 24-pixel thumb, shrinking the thumb to 20 pixels on hover and press while retaining a 150-millisecond state animation.

## Composition rules

- Use shared controls for repeated patterns; do not wrap every one-off layout preemptively.
- Keep page gutters, card padding, section gaps, and row gaps on the spacing scale.
- Preserve keyboard order, focus, tooltips for icon-only controls, contained errors, actionable empty states, and deterministic loading feedback.
- Avoid hover-only workflows, invisible unselected states, layout-shifting press effects, decorative animation, and ambiguous gray-on-gray body copy.
- Introduce a new token only for a reusable semantic role, not to encode a single screen coordinate.

## Baseline table scope

The current table primitive is intentionally foundational. Future table work may add column sizing, sticky headers, pagination, bulk selection, inline editing, saved views, and keyboard row navigation after real workflow review. Those additions must extend this primitive rather than create a competing table system.
