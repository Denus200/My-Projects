# Project Details Shell and Overview — Design QA

Date: 2026-08-28

## Evidence

- Primary visual sources: `C:\Users\Den\Downloads\Нова папка (2)\6\1\2\Projects_Expanded_Projects_Overview.svg` and `Tab.svg`; their paired PNGs were used as rendered references.
- Native Flet captures: `E:\Projects\Overlord\design-qa-assets\project-overview-polish-expanded.png` (1688 × 941 workspace), `project-overview-polish-collapsed.png` (1864 × 941 workspace), and `project-overview-polish-empty.png` (1688 × 941 workspace), using only the isolated deterministic demo database.
- Same-state combined comparison: `E:\Projects\Overlord\design-qa-assets\project-overview-polish-comparison.png`. The approved reference Sidebar was cropped before equal-workspace comparison.
- Runtime: Flet 0.84 native desktop renderer, Overlord light theme, `pixel_ratio=1.0`. Browser verification is intentionally inapplicable because Overlord's web product path is retired.

## Compared states

- Populated Project identity with Back, icon/color, title, Favorite, description, canonical Project Status Badge, More/Edit, and the global profile trigger.
- Shared Overview/Plan/Tasks/Notes & Files/Archive navigation with a stable 44-pixel tab height, one accent indicator, and one full-width neutral baseline.
- Populated Next Checkpoint, real Next Action Task, linked 12-Week Plan, active Project Plan, scalable Stage timeline, and current-stage progress.
- Completely new Project with no description, checkpoint, next action, linked cycle, active plan, or activity history; every approved structural card remains visible with an intentional empty state.
- Expanded and collapsed Sidebar workspace widths using the same flex/responsive card implementation.

## Findings

No actionable P0, P1, or P2 visual or functional differences remain inside the approved Project Details shell and Overview boundary.

- Header and tabs: the redundant right-side `All Projects` control is removed. Back uses the existing Projects route, More opens the existing Project editor, Status uses the canonical component, and all five tabs keep the same icon/text baseline as their active state changes. The neutral baseline is independent of the active accent indicator, and hover changes color/border only.
- Overview structure: the three summary cards share one 150-pixel shell and the main row uses an 8/4 responsive split for Plan Progress and Recent Updates. Borders, radii, padding, 16-pixel gaps, tinted leading icons, and optional open actions follow the reference.
- Data fidelity: checkpoint, Task status/date, linked Cycle week/range, plan title, ordered Stages, completed count, and current-stage Task completion ratio all come from existing Project/Task/Cycle data. No reference sample strings are hardcoded.
- Empty-state fidelity: missing values suppress misleading arrows while preserving the corresponding card and its explanatory label. An empty Project description is omitted cleanly.
- Activity limitation: the repository has no persisted Project-wide activity, event, history, or audit feed. Production therefore supplies no fabricated events and renders `No recent project activity`. The reusable activity component and event-type visual mapping are ready for real records if that product capability is approved later.
- Preserved scope: Plan, Tasks, Notes & Files, and Archive content was not redesigned; only their shared header/tab shell changed.

## Comparison history

1. P2 — The first native capture set a hidden scroll mode on short Stage collections, which caused the timeline to shrink to intrinsic width and collide. Short timelines now expand across the card; collections over five Stages use a fixed-width horizontally scrollable sequence.
2. Post-fix populated, collapsed, and empty captures were reviewed. The reference and final populated implementation were also opened together in one equal-workspace comparison. Remaining content differences are real demo data and the intentionally honest empty Recent Updates state.

## Verification

- `python -B -m unittest discover -s tests -p test_projects_redesign.py -v`: 15 tests passed in 38.034 seconds.
- `python -B -m unittest discover -s tests -p test_projects_ui_components.py -v`: 7 tests passed in 0.014 seconds.
- `python -B -m unittest discover -s tests -v`: 293 tests passed in 654.102 seconds.
- `python -B scripts/smoke_environment.py`: passed; no database opened.
- Changed Python modules and focused test modules compile successfully.
- Focused coverage verifies Back and edit actions, removal of `All Projects`, canonical Status Badge use, five stable tabs and active indicator, linked/unlinked Cycle states, filled/empty summary cards, real Next Action navigation/status, populated/empty Plan Progress, scalable Stage timelines, and reusable Recent Updates event mapping/empty state.

final result: passed

---

# Projects List Final Polish — Design QA

Date: 2026-08-28

## Evidence

- Primary component sources: `C:\Users\Den\Downloads\Нова папка (2)\6\1\1\Search.svg`, `Dropdown.svg`, `Multiselect.svg`, `Multiselect_Items.svg`, and `Cheak_box.svg`; paired PNGs were used only as rendered references.
- Native Flet captures: `E:\Projects\Overlord\design-qa-assets\projects-polish-expanded.png` (1688 × 941 workspace) and `projects-polish-collapsed.png` (1864 × 941 workspace), using the isolated deterministic demo database.
- Combined comparison inputs: `E:\Projects\Overlord\design-qa-assets\projects-polish-grid-comparison.png` and `projects-polish-controls-comparison.png`. The approved expanded-page reference Sidebar was cropped before equal-workspace comparison.
- Runtime: Flet 0.84 desktop renderer, Overlord light theme, `pixel_ratio=1.0`. Web/browser verification is intentionally inapplicable because the repository's web product path is retired.

## Compared states

- Expanded Sidebar: fixed 401 × 211 Project Cards, four columns, 12-pixel inter-card gap, and the Empty Project Card in the same wrapping grid.
- Collapsed Sidebar: fixed 354 × 211 Project Cards, five columns, 11-pixel inter-card gap, with immediate reflow back to four columns when expanded again.
- Search default/focus/entered configuration, including the 16-pixel Lucide magnifier, light stroke weight, 48-pixel suffix slot, source border, radius, and padding.
- Projects and Status multiselect closed/open state models, real options, count badges, full-row selection, reusable checkbox state, menu max height, and exclusive toolbar popup grouping.
- Recently updated single-select Dropdown and contextual Reset behavior.

## Findings

No actionable P0, P1, or P2 visual or functional differences remain in this focused patch.

- Grid: the wrapping row uses the existing workspace and the intentional Sidebar design state. It does not duplicate window or shell width calculations. Expanded and collapsed captures visibly contain four and five cards respectively on the first row.
- Controls: Search, Dropdown, Multiselect, Multiselect Item, and Checkbox are shared Presentation components. The corrected Search suffix no longer stretches the icon, the sort label is no longer clipped, and both multiselects share the same menu/item/checkbox implementation.
- Data and behavior: Project options come from the current Project summaries; Status options come from `ProjectStatus`. Project/status selections compose with Search and sorting, selected counts derive from the current selected sets, and Reset restores every default before hiding itself again.
- Preserved scope: Project Card geometry, notch path, Add Task affordance, colors, Status Badges, Metric Chips, internal spacing, Empty Card behavior, New Project placement, and existing navigation/actions were not redesigned.

## Comparison history

1. P2 — The collapsed 354-pixel card state retained a four-column grid because four 12-pixel gaps exceeded the available workspace by two pixels. The collapsed gap is now 11 pixels, producing the required five-column composition without shell-width arithmetic.
2. P2 — The Search suffix initially allowed the icon asset to expand to the field's suffix constraints. It now renders at the source-matched 16 pixels inside a fixed 48-pixel suffix slot.
3. P2 — The native Dropdown initially clipped the last character of `Recently updated`. Its shell is now 184 pixels wide and the full selected value is visible.
4. Post-fix reference/implementation comparisons were opened together and reviewed at native scale. Remaining content differences are intentional real demo data rather than copied reference strings.

## Verification

- `python -B -m unittest discover -s tests -p "test_projects*.py" -v`: 27 tests passed in 50.796 seconds.
- `python -B -m unittest discover -s tests -v`: 289 tests passed in 591.156 seconds.
- `python -B scripts/smoke_environment.py`: passed; no database opened.
- Focused coverage verifies 4→5→4 grid switching, fixed card widths, real Project and valid Project-status options, checkbox and full-row selection semantics, selected counts, multi-filter composition, single-select sorting, Search geometry/states, and Reset visibility/default restoration.
- Native closed-state captures passed visual review. Windows Graphics Capture could not persist an overlay-menu screenshot on this host (`SetIsBorderRequired failed: No such interface supported`), so popup open/close and selection behavior is covered by component/event tests rather than a saved overlay image.

final result: passed

---

# Projects Page UI-kit Alignment — Design QA

Date: 2026-08-27

## Evidence

- Primary component sources: `C:\Users\Den\Downloads\Нова папка (2)\6\Project_Card.svg`, `Status Badge.svg`, `Multiselect.svg`, `Multiselect_Items.svg`, and `Projects_Expanded.svg`. The paired PNGs were used as secondary rendered references.
- Native implementation captures: `E:\Projects\Overlord\design-qa-assets\projects-expanded.png` and `projects-collapsed.png`.
- Equal-viewport full comparison: `E:\Projects\Overlord\design-qa-assets\projects-expanded-comparison.png` (reference and implementation at 1920 × 1080, 1× density; the 1920 × 1017 native Flet content capture is bottom-padded only for equal-canvas review).
- Focused comparisons: `E:\Projects\Overlord\design-qa-assets\projects-toolbar-comparison.png` and `projects-card-comparison.png`.
- Runtime: native Flet 0.84 desktop renderer, Overlord light theme, isolated deterministic demo database, and `pixel_ratio=1.0`. Browser checks are intentionally inapplicable because Overlord's web product path is retired.

## Compared states

- Expanded production Sidebar with 401 × 211 Project Cards and the four-column 1920-pixel reference composition.
- Collapsed production Sidebar with 354 × 211 Project Cards and responsive grid reflow.
- Populated Project Card, stable top-right notch, circular Add Task action, per-Project color, hover-derived color, and full-card Project navigation.
- Empty Project Card with matching geometry, centered dashed affordance, full-surface Create Project action, and hover state.
- Canonical default/small and solid/subtle/text Status Badge variants; Project list usage for Active, Completed, Paused, and Archived states.
- Search, Projects multiselect, Status multiselect, single-select sorting, contextual Reset, and toolbar-level New Project.
- Live Search and real Project/status selections, sort changes, complete Reset semantics, Project opening, Add Task preselection, Create Project, and Sidebar reflow.

## Findings

No actionable P0, P1, or P2 visual or functional differences remain inside the approved Projects presentation boundary.

- Geometry and layout: the card shell uses the SVG's real contour as a native Flet canvas path. Its 16-pixel corner treatment, fixed 66-pixel notch, and 42-pixel Add Task control do not scale with card width. Expanded and collapsed Sidebar states use the specified 401- and 354-pixel widths, both at 211 pixels high, and the wrapping grid computes columns from the actual workspace.
- Card hierarchy: Status Badge, title, two-line description, three Project Metric Chips, and Last activity follow the supplied vertical composition. The old list-card favorite/star and Project-count result label are absent. The only top-right card action is Add Task for that Project.
- Color and interaction: persisted Project colors remain the base fills. Hover uses one reusable 10% darkening transform; Metric Chips use the requested translucent black overlay/border treatment rather than Status Badge colors. Empty-card hover uses the same derived treatment.
- Shared components: Search, Multiselect, single-select shell, Status Badge, Project Card shell, Project Metric Chip, and Empty Project Card live in the shared component layer. Page code owns data projection and callbacks rather than duplicated visual primitives.
- Toolbar: Search matches the 599 × 48 source geometry with its magnifier inside the right edge. Both multiselects use the count/label/chevron trigger and checkbox menu structure. Sort stays a true single-select, Reset clears Search/Project/status filters and restores default sorting, and New Project is aligned at the toolbar's far right.
- Responsive behavior: wide desktop preserves one horizontal toolbar; narrower widths allow logical wrapping without horizontal page overflow. Card widths are fixed to the requested Sidebar states, and native size animation softens the width change while the wrapping row performs the stable reflow.
- Accessibility and states: icon-only actions retain tooltips, search retains focus styling, shared checkbox semantics are preserved, labels use localized application strings, and reduced-motion tokens control the card size transition. Flet does not expose a native animated reflow equivalent to Figma Auto Layout, so sibling repositioning is immediate while card resizing is animated; stable layout takes priority as requested.
- Content differences in the comparison are intentional: the implementation shows real current demo Projects, valid domain statuses, real task counts, persisted colors, and current activity dates rather than copying the reference's sample content.

## Comparison history

1. P2 — Search initially placed the magnifier outside the field and shifted the toolbar geometry. It now uses the shared field's right-side suffix slot, and the Projects header/content gaps were aligned to the reference.
2. P2 — The default Status Badge was eight pixels narrower than the SVG. Default horizontal padding was corrected to the canonical component measurement; small badges retain their separate compact geometry.
3. P2 — The first native capture omitted packaged Lucide icons because the QA runtime did not receive the repository assets directory. The capture configuration was corrected and the final evidence includes the actual Sidebar, toolbar, and action icons.
4. Post-fix expanded, collapsed, toolbar, and card comparisons were reviewed at native scale. Remaining variation is confined to real data, the retained sort/Reset behavior explicitly requested in the brief, and the supported native-renderer limitations described above.

## Verification

- `python -B -m unittest discover -s tests -v`: 287 tests passed in 779.279 seconds.
- New focused coverage verifies fixed notch geometry in both Sidebar states, Metric Chip overlays, Search and Multiselect geometry/selection, canonical Status Badge variants, Project/Card action separation, empty-card full-surface creation, Sidebar width mapping, Search/Reset behavior, and absence of the legacy favorite UI.
- Architecture coverage confirms that active UI uses shared form factories, raw UI-kit colors remain centralized in semantic tokens, Presentation boundaries are preserved, local Lucide assets are used, and page construction remains compatible with Flet 0.84.
- Native visual QA used only `data/demo/overlord_demo.db`; deterministic seeding remains isolated and `data/overlord.db` was never opened or modified.

final result: passed

---

# Prior Projects Foundation and Detail-Flow Design QA

## Comparison target

- Visual source of truth: PNG references under `E:\Projects\Overlord\Ref\Deteil\Projects`.
- Native implementation captures: `E:\Projects\Overlord\artifacts\projects`.
- Combined reference/implementation evidence: `E:\Projects\Overlord\artifacts\projects\comparisons`.
- Viewports: 1688 × 941 logical pixels for content beside the expanded production Sidebar; 1864 × 941 beside the collapsed Sidebar; 499 × 635 for Create Project.
- Theme and runtime: Overlord light theme, native Flet desktop renderer, deterministic isolated demo database, `pixel_ratio=1.0`. Browser verification is not applicable because Overlord's web product path is intentionally retired.
- Sidebar handling: the supplied reference Sidebar was cropped before comparison, as required. No production Sidebar structure or styling was changed.

## Compared states

- Projects list with expanded and collapsed production Sidebar widths.
- Real Project colors, Active/Completed/Archived lifecycle badges, Favorites, Task counters, filters, sorting, and add-Project tile.
- Create Project with name, description, persisted color, Project status, and explicit Stay/Plan/Tasks destination.
- Overview both without and with a linked active 12-week Cycle.
- Project Plan with active plan and ordered Stage data.
- Project Tasks in All Tasks and By Stage modes, using the production compact Task Card.
- Notes & Files with local Markdown content and imported-file metadata.
- Archive with plan history and reversible Project archive action.
- Shared Overview/Plan/Tasks/Notes & Files/Archive tabs.

## Findings

No actionable P0, P1, or P2 visual differences remain inside the approved product/data boundary.

- Hierarchy and geometry: the implementation follows the reference's page/header/tab/content hierarchy. The Project grid resolves to four columns at the expanded content width and five at the collapsed content width, with no horizontal overflow. Card descriptions, all three counters, last activity, and the add tile remain visible.
- Create Project: the dialog uses the reference size and field order, a full-width form, the selected pink swatch, segmented destinations, and a close action. The neutral destination is labeled “Stay in Projects” so its tested behavior is explicit: create, close, and do not force a Plan or Tasks redirect.
- Project identity and states: card surfaces use persisted Project colors; Favorite is independent from lifecycle status; shared status badges expose only valid Project states. More opens the edit flow.
- Overview: the linked 12-week block is entirely absent for an unlinked Project and populated from the active Cycle relationship for a linked Project. Project Plan and global 12-week Cycle data remain visually and architecturally separate.
- Plan and Tasks: Stage cards and By Stage grouping use persisted Stage ownership. Project Tasks reuse the shared compact Task Card as required instead of reproducing the reference's separate task-table presentation.
- Notes & Files: the three-area workspace preserves the reference hierarchy while rendering actual Markdown and local file metadata. No file content is stored as a database blob.
- Archive: the page distinguishes plan history and reversible Project archive state. Archiving never deletes Tasks or Task links.
- Typography, borders, radii, spacing, controls, and interaction colors use the existing semantic design system. Raw page colors were moved into the centralized Project palette token, and every icon uses a tintable local Lucide asset.

## Expected product-data constraints

The reference includes richer checkpoint history, activity events, per-stage checkpoint detail, archived-resource metadata, and actual/active time. Those models do not exist in the approved Foundation scope. The implementation omits those data-dependent blocks or shows the existing honest “Not tracked yet” state instead of fabricating production values. Work Sessions, a new activity ledger, and individual note/file archive workflows remain separate product decisions.

## Comparison history

1. Initial native captures exposed transparent capture framing and a 1264-pixel window constraint. The harness now supplies the light background and resizes the native window to the exact reference content width.
2. The first wide list rendered six columns and clipped lower card metadata. The responsive grid was corrected to the reference's four expanded/five collapsed pattern, card height was made content-driven, and the add-Project tile was added.
3. Project detail initially repeated the title/description in a second body header. The duplicate identity row was removed while Favorite, status, edit, and back actions remain in the shared page header.
4. Create Project initially used radio controls and narrow intrinsic fields. It now uses full-width fields, segmented destinations, the reference default swatch, and a close control.
5. All Tasks/By Stage initially represented selection through disabled-button styling. Both modes now use the shared selected-button state and produce unambiguous captures.
6. New reference-derived icons initially retained fixed black strokes. All registered Lucide assets now use `currentColor` and pass the repository packaging/tintability contract.

## Verification evidence

- Representative native captures and all nine combined comparisons exist under `artifacts/projects`.
- Focused Project, migration, Dashboard/Task Card, task-workspace, localization, boundary, and presentation tests pass. The final full run passed 213 of 214 tests.
- Disposable production-copy migration reached schema v10 with rows preserved, a validated backup, clean integrity, and zero foreign-key violations; the production source hash and size were unchanged.
- One unrelated full-suite U2 test remains date-sensitive: on 2026-08-21 it schedules a Task for today but hardcodes a 2026-08-16 deadline, so existing schedule validation correctly rejects the Task. This is not a Projects regression.

## Follow-up iteration notes

- P3: if checkpoint/activity/archive-resource models are approved later, the corresponding reference-rich panels can replace the deliberately omitted data blocks.
- P3: physical Windows scaling/theme checks remain manual beyond the deterministic light-theme native captures.

final result: passed

---

# Dashboard Weather Widget — Design QA

Date: 2026-08-27

## Evidence

- Visual sources: `Weather Card.svg/png`, `Wisual.svg/png`, and `Tag_Card_weather.svg/png` supplied with the Weather request. SVG geometry and sampled filter colors are primary; PNGs confirm the rendered intent.
- Native Flet captures: `artifacts/dashboard-weather/01-sunny.png` and `02-rainy.png` at the reference card viewport of 448 × 461 logical pixels.
- Equal-viewport comparisons: `artifacts/dashboard-weather/comparison-sunny.png` and `comparison-rainy.png`, each placing the exact 448 × 461 reference crop beside the native implementation.
- Runtime: supported native Flet desktop renderer, Overlord light theme, production Open-Meteo provider for Merefa, deterministic provider for visual QA/tests, and `pixel_ratio=1.0`. Browser verification is not applicable because Overlord's web product path is intentionally retired.

## Compared states

- Sunny default state and Rainy selected-day state.
- City, high/low values, current temperature, condition copy, circular animation, themed Lucide icon, and five-day selector.
- Card geometry, 300-pixel weather visual, 192-pixel glass region, selected tab, 16-pixel radius, and reference surface/border colors.
- Weather-specific layered shadows and the independent GIF/shadow composition.

## Findings

No actionable P0, P1, or P2 visual differences remain inside the approved Flet boundary.

- The component matches the 448 × 461 card and 300 × 300 animated visual geometry from the SVG. The lower glass region starts at y=269 and preserves the visual relationship with the sphere behind it.
- Flet cannot reproduce Figma's physical refraction, depth, dispersion, or inner-shadow model one-to-one. The implementation uses a 10%-white backdrop layer, Gaussian backdrop blur with sigma 12, and a low-opacity preset-tinted top border. This is a close native approximation rather than a claim of filter parity.
- The GIF is a separate `Image` layer. A separate circular carrier owns five `BoxShadow` layers using the source-sampled darkest group colors: Sunny `#8D3C07`, Rainy `#192776`, Cloudy `#415D7C`, and Snowy `#526A82`.
- The selected day updates the normalized forecast state, animation asset, shadow stack, Lucide icon, icon tint/background, high/low values, temperature, and condition copy in place. It does not rebuild or navigate the Dashboard.
- The implementation fits all five day actions inside the card so every tab remains usable. The supplied first-card crop clips part of the fifth label; that clipping was not reproduced because it conflicts with the explicit usability requirement.
- The native comparison caught a one-pixel temperature control caused by a Flet height interpretation. The final implementation removes that invalid constraint and matches the reference's large number with a smaller `°C` unit.

## Verification

- Twelve focused Weather tests pass for the exact Open-Meteo request, current/daily normalization, WMO grouping, malformed responses, cache round-trips, offline fallbacks, refresh cadence, request-free Dashboard relayouts, exact placement under the top row, card/glass geometry, visual presets/assets/shadows/icons, and in-place day switching.
- All 20 pre-existing Dashboard top-row/board tests pass unchanged.
- The repository-wide regression run passes all 280 tests.
- Native Sunny and Rainy captures and both combined comparisons were regenerated after the typography fix and reviewed at original resolution.
- The capture path uses no database and never opens `data/overlord.db`.
- A live provider check returned five dated Merefa forecasts and normalized the current day to 17°C, high 20°C, low 14°C, Overcast, and the existing Cloudy visual family.

## Known native limitations

- Flet exposes Gaussian backdrop blur but not Figma's exact light/refraction/depth/dispersion controls or true inset shadow, so glass optics and selected-tab shadow are close native approximations.
- GIF frame timing and blur softness can vary slightly with Windows GPU/render scale; the component geometry remains fixed at the approved preferred card size.
- Location and units are intentionally fixed to Merefa and Celsius in this tranche; there is no location search, GPS, or settings surface yet.
- Cached data remains visible after refresh failures, but the approved card does not currently expose cache age or a manual refresh action.

final result: passed

---

# Dashboard Top Row — Responsive Board and Weekly Progress Design QA

Date: 2026-08-26

## Evidence

- Visual source: `C:\Users\Den\Downloads\Нова папка (2)\5\Frame 318.png` and `Weekly Progress.png`, with their paired SVG geometry as the primary source.
- Native Flet captures: `artifacts/dashboard-top-row/01-wide-1640x433.png`, `02-narrow-1120x433.png`, and `03-extra-wide-1816x433.png`.
- Equal-viewport comparison: `artifacts/dashboard-top-row/comparison-wide.png`, with the 1640 × 433 source and implementation placed side by side.
- Runtime: supported native Flet desktop renderer, light theme, deterministic disposable database, and `pixel_ratio=1.0`. Browser verification is not applicable because Overlord's web path is intentionally retired.

## Findings

- The Three-Day Board and Weekly Progress share one 433-pixel-high row with a 16-pixel gap. The board retains its 1176-pixel expanded-Sidebar and 1300-pixel collapsed-Sidebar maxima; Weekly Progress uses 448 pixels as its comfortable reference width and expands into all remaining Row space.
- The board preserves the accepted Task Card, add-task, date-chip, internal ListView, and subtle day-divider presentation. No Dashboard content below the top row or shell styling changed.
- Weekly Progress matches the reference hierarchy and geometry: title/date chip, seven 160-pixel tracks, completion gradients, current-day label, two dividers, and four aligned metrics. Its seven flexible day columns and paired metric columns distribute the additional width shown in the 1816-pixel capture without stretching the board.
- Chart values, Execution Score, and Completed/Planned are read from the selected week's Tasks. Active Time and Total Time are separately aggregated from their corresponding persisted Task fields; missing data keeps the honest `Not tracked yet` state.
- At 1120 pixels of available row width, Yesterday is hidden and Today plus Tomorrow remain beside Weekly Progress. Below the second board breakpoint, Tomorrow also hides while Today and Weekly Progress remain. Restoring width reveals the columns again on the same mounted controls.
- Source/implementation content differs intentionally because the implementation capture uses real disposable Task records and therefore does not reproduce the reference's internally inconsistent sample values (`85%` and `50/60`). No actionable P0, P1, or P2 visual mismatch remains in the approved scope.

## Verification

- Focused Dashboard presentation tests cover expanded/collapsed maxima, resize, maximize/restore, ordered day hiding, restoration without navigation, seven real bars, and separate time metrics.
- Application coverage verifies weekly time aggregation, week exclusion, NULL handling, and separation of Active Time from Total Time.
- The final repository-wide regression run passes all 268 tests.
- The native capture harness uses only `data/test-tmp/dashboard-top-row-qa.db`, removes it after capture, and never opens `data/overlord.db`.

final result: passed

# Create Task Redesign — Tranche 1 Design QA

## Evidence

- Visual source: every PNG under `Ref/Deteil/Tasks/Create Task`, plus `Root Frame.png` and `Root Frame+Time.png`.
- Native Flet captures: `artifacts/create-task/01-default.png` through `10-deadline-picker-overlay.png`.
- The seven Create Task exports were deduplicated as dynamic combinations of advanced visibility, Project/Stage selection, Deadline, duration, and Checklist state. No frame-specific component was created.

## Compared states

- Default and advanced-open modal states.
- Multiple Projects and two independent same-Project Stage selectors.
- Deadline and hour/minute Estimated Time values.
- Checklist and large scrollable Checklist states with fixed Save/Cancel actions.
- Date-only and date+time calendar overlays visibly stacked above the preserved Create Task modal.

## Findings

- The implementation follows the 600-pixel reference modal, full-width base fields, three-control advanced row, full-width Stage dependency rows, crimson primary action, progressive Checklist workspace, and independent overlay hierarchy.
- The reference's 12-Week Plan controls are intentionally absent because the approved tranche explicitly defers that integration.
- The implementation uses actual Project titles/colors and available Stages rather than reference sample data.
- The custom date/date-time overlay uses the same calendar renderer with a conditional time row. Cancel closes only the top overlay and retains the Create Task form state.
- Large Checklists scroll inside the content region while the action row remains accessible.

final result: passed with the explicitly deferred 12-Week Plan controls omitted

---

# Task Details Redesign — Tranche 2 Design QA

## Evidence

- Visual source: all three PNG states and paired SVG geometry under `Ref/Deteil/Tasks/Task Details`.
- Native Flet captures: `artifacts/task-details/01-basic-task-details.png` through `09-delete-confirmation.png`.
- The reference exports were deduplicated as data-density states of one component: multiple Projects, available Project Stage rows, Checklist density, and a sample 12-Week relation.

## Compared states

- Basic Task Details and a Task with multiple Projects.
- Independent same-Project Stage selectors.
- Estimated Time with a three-digit `150 h` value and a true blank/NULL estimate.
- Nested Checklist, completion progress, and large scrollable Checklist.
- Persisted Paused lifecycle badge.
- Destructive Delete confirmation over the preserved Task Details modal.

## Findings

- The implementation follows the 600-pixel reference modal, header action order, full-width Title/Description/Date fields, three-control metadata row, dynamic Stage rows, Checklist workspace, and fixed crimson Save/Cancel footer.
- Missing Estimated Time renders blank hour/minute inputs and persists `NULL`; it does not display a fake `0 h 0 min`. The widened hour field visibly supports `150` without clipping.
- The status selector exposes only Planned, In progress, Blocked, Paused, and Completed. Blocked remains derived from an open Blocker; Paused uses its persisted lifecycle value.
- Delete uses the local Lucide `trash-2` asset and a compact application-consistent confirmation with a distinct destructive action.
- The reference's 12-Week row is intentionally absent because Cycle editing was excluded from this tranche. Existing Cycle links remain unchanged during Task Details saves.
- Total Time, Active Time, completion-time entry, and final estimate locking are intentionally absent for Complete Task tranche 3.

final result: passed with Cycle editing and Complete Task time fields explicitly deferred

# Complete Task — Tranche 3 Design QA

Date: 2026-08-21

- Visual source: `Ref/Deteil/Tasks/Complete Task.png` and its paired SVG geometry.
- Native Flet captures: `artifacts/complete-task/01-existing-estimate-read-only.png` through `06-completed-result.png`.
- Verified an existing read-only estimate, a missing editable estimate, entered estimate, entered Total/Active values, fully visible 150-hour values, and the completed Task result.
- The shared duration control preserves distinct `h` and `min` suffixes, 3+ digit hours, 2 digit minutes, and the `0–59` minute contract.
- The modal uses semantic tokens, packaged Lucide close/check icons, field labels, a compact stacked form, and explicit Save/Cancel actions.
- Opening, cancelling, and closing do not complete the Task. Save confirms one atomic Application command; no timer, inferred duration, Work Session, or analytics UI was introduced.

final result: passed for the six required native Complete Task states

---

# My Tasks — Kanban View Redesign Design QA

Date: 2026-08-22

## Evidence

- Visual sources: `Ref/Deteil/Tasks/My Tasks/Kanban/Tasks_Kanban_Expanded.png` and `Tasks_Kanban_Collapsed.png`, with their paired SVG geometry.
- Implementation captures: `artifacts/tasks-kanban/01-expanded-sidebar.png` and `02-collapsed-sidebar.png`, plus internal-scroll, Project-filter, search-filter, and moved-card result states through `06-drag-moved-result.png`.
- Viewport and density: source and implementation were captured at 1920 × 1080 pixels at 1× density in the light theme. Expanded and collapsed Sidebar states were compared at the same viewport.
- Full-view comparisons: `artifacts/tasks-kanban/comparisons/expanded-full.png` and `collapsed-full.png`.
- Focused comparisons: `artifacts/tasks-kanban/comparisons/expanded-toolbar.png` and `expanded-columns.png`.

## Findings

- Typography uses the current shared text styles while matching the reference hierarchy and compact control heights. The user-requested title is `My Tasks`; the older reference title `Tasks` is intentionally superseded.
- Layout matches the measured reference geometry at 1920 × 1080: a 24-pixel page inset, 48-pixel toolbar, 16-pixel column gaps, 322-pixel expanded columns, 356.2-pixel collapsed columns, and a 16-pixel bottom inset. Narrower desktop widths retain all four columns through horizontal board scrolling rather than collapsing the task workflow.
- Every Kanban column owns an independent vertical ListView beneath a fixed header. The page shell does not grow with long columns.
- Colors, borders, radii, state feedback, and icons use existing semantic tokens and packaged Lucide assets. No page-local raw color system or parallel card implementation was introduced.
- Cards use the shared full Task Card with real Project metadata. The existing six-dot drag control remains the sole card reorder/move affordance and reveals on hover instead of adding default-state chrome.
- Search updates live and on submit; the Project selector uses normalized multi-Project membership. Filtering projects the full canonical order without deleting hidden task positions.
- Needs Attention is a Presentation-only grouping of canonical missed/archive placement, Paused Tasks, and Tasks with open Blockers. It is intentionally non-assignable. Completed moves still use the canonical Complete Task flow, and task creation/details remain shared.
- Reference-only sample content, the photographic avatar, and unfinished Sidebar destinations were not copied. The implementation keeps the current shell, shared avatar, real QA dataset, and honest Needs Attention cards.
- Native desktop interaction and regression coverage verified tabs, creation entry points, filtering, independent overflow, card/column ordering, valid moves, Complete Task routing, and shared details. Browser console checks are not applicable because Overlord intentionally has no supported web runtime.

## Comparison history

1. P0: the first native board capture produced zero-width flex columns. The board received explicit responsive dimensions and exact reference-height calculations.
2. P1: the expanded toolbar wrapped when the native capture held stale page-width state. The workspace now derives its width from the active Sidebar state, and the deterministic capture sets the exact 1920 × 1080 state before rendering.
3. P2: initial segmented tabs used filled-button defaults, cards exposed drag handles at rest, and header/background density drifted. Tabs moved to a shared TextButton segmented surface; handles became hover-revealed; column header, surface, spacing, and token usage were aligned.
4. P2: the empty search field omitted the permanent right-side search icon visible in the reference. Kanban now wraps the shared search field with a fixed Lucide overlay without changing existing callers.
5. Final combined comparisons show no actionable P0, P1, or P2 mismatches. Remaining differences are intentional current-product content and shell differences described above.

## Verification

- The repository-wide run completed 247 tests with 245 passing and only two stale assertions that still expected the superseded `Tasks` title. After correcting those rename-contract assertions, all 16 runtime tests passed in isolation.
- After the final narrow-width horizontal-scroll change, all 16 Task workspace tests passed again. Changed Python modules compile, the environment smoke check passes without opening a database, and the scoped diff check reports no whitespace errors.
- The capture harness uses only `data/test-tmp/tasks-kanban-qa.db`; that disposable database is absent after QA. `data/overlord.db` was never opened or modified.

final result: passed

---

# My Tasks — Week View Redesign Design QA

Date: 2026-08-22

## Evidence

- Visual sources: `Ref/Deteil/Tasks/My Tasks/Week/Tasks_Week_Expanded.png` and `Tasks_Week_Collapsed.png`, their paired SVG geometry, and the collapsed/expanded Week states in `Ref/Deteil/Component/Tabs.png` and `Tabs.svg`.
- Implementation captures: `artifacts/tasks-week/01-expanded-sidebar.png` through `07-expanded-week-navigation.png`, covering both Sidebar states, later-day horizontal position, internal day overflow, Search, Project filtering, and expanded navigation.
- Viewport and density: source and implementation are 1920 × 1080 pixels at 1× density in the light theme. The Tabs focused comparisons use equal 560 × 80 crops from the source state and implementation toolbar.
- Full-view comparisons: `artifacts/tasks-week/comparisons/expanded-full.png` and `collapsed-full.png`.
- Focused comparisons: `expanded-toolbar.png`, `expanded-week-board.png`, `week-tab-collapsed.png`, and `week-tab-expanded.png` in the same comparison directory.

## Findings

- Fonts and typography use the current shared Overlord text hierarchy and no longer wrap inside the compact or expanded Tabs states. The user-approved product title remains `My Tasks`; the older source title `Tasks` is intentionally superseded.
- Spacing and layout match the measured 1920 × 1080 geometry: 24-pixel page inset, 48-pixel toolbar, columns beginning at y=136, 300-pixel day width in both Sidebar states, 16-pixel column gaps, 928-pixel working height, and a 16-pixel bottom inset.
- The Week board is one seven-day horizontal sequence. Each day header remains fixed above an independent vertical ListView, so overflow does not grow neighboring columns or the page.
- Colors, borders, radii, focus/today treatment, and icons use existing semantic tokens and the packaged Lucide registry. The minus control adds the matching Lucide asset rather than a text glyph or custom drawing.
- Image and asset fidelity: the Week content contains no reference-specific raster imagery. The current packaged Overlord mark, Lucide icons, and shared profile treatment are preserved; no placeholder or generated imagery was introduced.
- Copy and content use localization-backed labels. Dates, counts, Search results, and Project-filter results come from real Tasks rather than the source's sample dates or hardcoded counts.
- Cards reuse the shared full Task Card, Project color indicators, Task Details opener, and canonical Complete Task callback. Per-day plus actions reuse Create Task with the selected date prefilled.
- Previous, Today, and Next are integrated into one shared expandable Tabs component for Week and Month. Expansion is transient and resets on every view change; Month content itself was not redesigned.
- Cross-day Week drag-and-drop remains intentionally absent because the pre-existing Week view had no safe persisted move interaction. Task Details date editing remains the canonical way to move a Task between days, as allowed by the tranche brief.
- Browser console verification is not applicable because Overlord intentionally supports only the native Flet desktop runtime. Native captures and Flet interaction tests cover the requested states.

## Comparison history

1. P2: the first native implementation capture wrapped `Week` and `Month` inside compact expandable tab segments because default button padding consumed the reduced label width. The shared segmented-tab style now applies compact horizontal padding only to constrained segments.
2. Post-fix captures show single-line labels in both the 273-pixel collapsed Week surface and 517-pixel expanded Week surface. No actionable P0, P1, or P2 mismatch remains; current dates/data, the My Tasks title, shared avatar, and current Sidebar destinations are intentional product differences.

## Verification

- All 21 focused Task workspace tests pass, including accepted Kanban behavior, seven-day geometry, horizontal/internal scrolling contracts, counts, Search plus normalized multi-Project filtering, contextual Create Task, date-derived movement, shared full cards, expandable Week/Month reset sequences, and previous/today/next navigation.
- Localization, presentation construction, icon packaging, pure workspace projections, and all 19 U2 Task flow tests pass. Changed Python modules and QA scripts compile.
- The final repository-wide regression run passes all 252 tests.
- The capture harness uses only `data/test-tmp/tasks-week-qa.db`; it removes that disposable database after capture and never opens `data/overlord.db`.

final result: passed

---

# My Tasks — Month View Redesign Design QA

Date: 2026-08-22

## Evidence

- Visual sources: `Ref/Deteil/Tasks/My Tasks/Month/Tasks_Month_Expanded.png` and `Tasks_Month_Collapsed.png`, with their paired SVG geometry.
- Implementation captures: `artifacts/tasks-month/01-expanded-sidebar.png` through `07-project-filtered.png`, covering both Sidebar states, current/next month navigation, a busy date, Search, and normalized Project filtering.
- Viewport and density: source and implementation are 1920 × 1080 pixels at 1× density in the light theme.
- Full-view comparisons: `artifacts/tasks-month/comparisons/expanded-full.png` and `collapsed-full.png`.
- Focused comparisons: `expanded-toolbar.png`, `expanded-month-grid.png`, `collapsed-month-grid.png`, and `busy-day-grid.png` in the same comparison directory.

## Findings

- Fonts and typography use the accepted Overlord hierarchy while matching the reference's quiet 12-pixel weekday, date, and empty-state labels. The earlier source title `Tasks` is intentionally superseded by the user-approved `My Tasks` title.
- Layout matches the reference composition: a fixed shared toolbar, Monday–Sunday labels, seven responsive equal-width columns, 8-pixel row/column gaps, 164-pixel fixed-height cells, and vertical Month scrolling for required fifth/sixth calendar rows. Expanded and collapsed Sidebars reuse one implementation and keep all seven columns aligned.
- Calendar dates come from `calendar.monthrange` plus `date`/`timedelta` calculations. The matrix includes only the real leading/trailing dates needed to complete its rectangular week rows, and navigation regenerates the full matrix rather than changing a label alone.
- Current day uses the semantic crimson outline dynamically. Adjacent-month cells use the existing muted inner-surface token while remaining interactive real dates that can display scheduled Tasks.
- Each day keeps its date and add action fixed above an independent compact-card ListView. Busy dates retain the 164-pixel cell height and expose all Tasks by internal scrolling instead of stretching their calendar row or silently hiding content.
- Month reuses the accepted compact Task Card, including completion state, title ellipsis, and up to four real Project color indicators. Pending cards retain the compact component's existing completion affordance even though the older reference shows it only for completed sample rows; this preserves the shared canonical Complete Task entry point rather than forking a Month-only card.
- Date-level plus actions open the canonical Create Task flow with that real cell date prefilled. Task titles open the shared Task Details dialog; completion uses the canonical Complete Task confirmation; saved date changes and deletion refresh the date-derived projection without duplication.
- Search and normalized multi-Project filtering change only the Task content and `No Tasks` state inside cells. Calendar cells, Task dates, Task order, and relationships remain unchanged; clearing filters restores the underlying Tasks.
- The accepted expandable Month Tabs behavior is unchanged. Previous and Next shift exactly one calendar month across year boundaries, Today returns to the current month, and switching views resets expansion through the existing transient Presentation state.
- Month drag-and-drop was not present. Cross-date drag-and-drop remains deferred because adding it safely would require a new canonical persisted date-move command; no parallel DnD architecture was introduced, and Kanban/Week behavior remains untouched.
- Colors, borders, radii, icons, and surfaces use existing semantic tokens and packaged Lucide assets. The screen has no raster imagery beyond the accepted shell avatar; no placeholder or handcrafted visual assets were introduced. Browser console checks are not applicable because Overlord intentionally has no supported web runtime.

## Comparison history

1. P2: the first native comparison rendered every day-level plus action as a filled tertiary-button pill, while the source uses a bare icon. The Month cell now exposes a transparent 24-pixel semantic target around the packaged Lucide plus.
2. The revised 1920 × 1080 expanded, collapsed, grid, toolbar, and busy-day comparisons show no remaining actionable P0, P1, or P2 differences. Differences in dates, Task titles, avatar, current-day position, and adjacent-date count are intentional real-data/current-product differences.

## Verification

- Focused model coverage passes for four-, five-, and six-row calendar matrices, leap-year February, Sunday-start months, and December/January transitions.
- Focused Task workspace coverage passes for Monday-first geometry, both Sidebar states, adjacent dates, dynamic today state, contextual creation, date-derived movement, shared details/completion/deletion, Search plus normalized multi-Project filtering, lifecycle visibility, compact cards, busy-day overflow, and Month navigation. The same suite regression-tests accepted Kanban, Week, and shared Tabs behavior.
- The final repository-wide regression run passes all 260 tests.
- Native captures use only `data/test-tmp/tasks-month-qa.db`; the harness removes that disposable database and never opens `data/overlord.db`.

final result: passed
