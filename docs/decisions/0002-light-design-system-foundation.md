# Decision 0002: Light Design System Foundation

Date: 2026-08-11

## Status

Accepted.

## Context

Foundation v0.1 centralized a Crimson Focus palette and several shared presentation components, but active controls still relied on inconsistent Flet defaults and local constructor options. Primary actions, inputs, dropdowns, checkboxes, selectable surfaces, and future tables did not share one complete interaction-state model.

The product requires a usable light-theme baseline before page-by-page visual redesign. It must fit the existing Python/Flet architecture and must not create a generated design system parallel to `overlord/ui/design_system`.

## Decision

Keep `overlord/ui/design_system` as the only design-system source. Extend it with semantic interaction/control tokens and state-aware Flet styles. Expose reusable constructors through `overlord/ui/components/controls.py`, and migrate active form controls to those constructors.

Retain Crimson Focus, Segoe UI, Lucide-only interface icons, 4-pixel spacing rhythm, compact desktop density, clear keyboard focus, and reduced-motion behavior. Treat the light theme as the visual redesign baseline. Preserve dark-theme state parity without claiming a final dark redesign.

On 2026-08-12, the approved Sidebar reference replaced the text brand fallback with the supplied Overlord SVG mark and refined the mounted navigation without changing routes or persistence. The expanded rail remains 232 pixels; the compact rail becomes 56 pixels. Active, hover, pressed, disabled, collapse/expand, and language-toggle states now use explicit semantic tokens derived from the approved component references. Navigation and header actions use borderless custom interaction surfaces so native button chrome cannot alter the reference geometry.

Do not persist UI/UX Pro Max output into its generated `design-system/MASTER.md` hierarchy. Its database is advisory research; approved product decisions and code/runtime evidence remain authoritative.

## Consequences

- Existing pages gain consistent control geometry and interaction states without changing Domain, Application, Infrastructure, navigation, or persistence boundaries.
- New pages can use explicit button, input, select, checkbox, choice-chip, and table primitives.
- Page-level HEX colors and local copies of control state maps remain prohibited.
- Future visual work extends the existing tokens and primitives instead of introducing a second system.
- The initial table is intentionally basic; advanced behaviors require later workflow evidence.
