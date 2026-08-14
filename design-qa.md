# Profile Header and Task Reordering — Design QA

## Source References

- `C:\Users\Den\Downloads\Нова папка (2)\0\Frame 33.svg` — Profile Menu Trigger source of truth: 76×40 white pill, 20px radius, 32×32 circular avatar at 4px inset, and a 2px black chevron.
- `C:\Users\Den\Downloads\Нова папка (2)\0\Frame 32.svg` — Dashboard greeting source of truth: approximately 247×51 with a compact two-line title/subtitle rhythm.
- Both SVG files were audited from their vector markup. The available image viewer cannot render these SVG files directly, so the measurements, fills, paths, and typography bounds were taken from the source markup.

## Implemented Surfaces

- The shared Page Header now owns one unified 76×40 Profile Menu Trigger with a white semantic surface, 20px radius, 32×32 avatar, and locally registered Lucide chevron aligned to the SVG path geometry.
- The Dashboard greeting remains dynamic while using a compact 51px title/subtitle block derived from `Frame 32.svg`.
- One explicit shared content-padding layer owns the effective 24px horizontal and 16px vertical page padding. The App Shell and outer scroll surface add no compensating page padding.
- A shared six-dot task drag-handle surface now adapts to native Dashboard reordering and Tasks/Kanban dragging without making the card body draggable.

## Functional and Structural Verification

- Accessibility inspection of the running native demo confirmed the dynamic Dashboard greeting/count, unified profile trigger semantics, and visible task drag handles.
- Automated tests verify exact profile/header geometry, one-layer page padding, stable Dashboard reorder keys, handle-only Kanban dragging, valid cross-column state changes, and persisted Today ordering.
- The complete test suite passed: 164 tests.
- Environment smoke check passed without opening the production database.
- Python compilation and `git diff --check` passed.

## Fidelity Mapping

- Typography: application text remains live; title uses 24px/W700 with compact line height, subtitle uses 14px with compact line height, within a 51px header block.
- Spacing: profile geometry is 76×40/20px radius/4px avatar inset/32px avatar; global page spacing is 24px horizontal and 16px vertical from one content layer.
- Colors: profile white/black values are semantic design-system tokens, not raw page/component colors.
- Icons: chevron and grip use the repository's local Lucide registry.
- Copy: configured display name and live Today task count are retained; no text from the SVG is embedded or hardcoded.

## Visual QA Blockers

- [P1] A source-versus-implementation screenshot comparison could not be produced. Windows native graphics capture failed twice with `SetIsBorderRequired failed: No such interface supported (0x80004002)`, and the Flet screenshot fallback did not mount before timing out. Required action: visually inspect the native demo in a Windows session with working Graphics Capture.
- [P1] Real pointer gesture verification could not be completed in this session because the native window geometry was unavailable and accessibility input could not target the Flutter surface. Automated tests verify the handle wiring, reorder callbacks, state transitions, and persistence, but they cannot sign off the physical press-drag feel. Required action: manually drag one Dashboard card and one Tasks/Kanban card by their six-dot handles.

## Comparison History

- Source SVG geometry and styling were audited before implementation.
- Implementation structure, accessibility state, and behavior were verified after implementation.
- Side-by-side visual comparison remains blocked by native capture failure; no unverified screenshot was substituted.

final result: blocked
