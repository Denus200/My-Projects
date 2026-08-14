# UX Phase U5 - Foundation Hardening

Status: implemented on 2026-08-07.

Automated result: 102/102 repository tests passed in 197.368 seconds. The environment smoke check passed without opening a database. Production database SHA-256 before and after U5 is `CAB5F06039D815C5B19AB7A840F068AE23E6F7BF8D15EF2E9269DFB5786435DE`; integrity is `ok`, the schema is version 6, and there are zero foreign-key violations.

## Scope and data safety

U5 changes Presentation, Presentation tests, and Foundation documentation only. It adds no feature, migration, Domain entity, repository method, Application service, or demo seed change. Goals, Habits, Skills, Work Sessions, Weekly Reviews, AI, desktop Widget behavior, notifications, cloud sync, accounts, collaboration, and new analytics remain deferred.

## Settings

Settings now contains Appearance, Planning, and Startup categories. A constrained desktop rail selects a compact content panel; a narrow-width selector replaces the rail below the Foundation breakpoint, including when the window crosses that breakpoint while Settings is open. System, Light, and Dark remain the only theme choices. Motion, reduced motion, first day of week, default Cycle length, startup destination, and collapsed-sidebar preference retain their existing persistence behavior. Future Widget presentation was removed.

## Shared hardening

- The mounted App Shell remains stable during navigation, Settings saves, theme changes, and responsive Settings changes.
- Page/section headings, setting rows, dialog footers, Task rows, contained states, and non-blocking success feedback use shared established patterns.
- Semantic Flet theme defaults now cover focus, hover, disabled controls, dividers, cards, dialogs, and buttons using the approved Crimson Focus tokens.
- Stable navigation, shell, state, error, success, Settings, and common Task-row copy is served from the centralized English catalog.
- Route failures show neutral copy and a correlation ID while technical exceptions remain in logs.
- Static boundary tests continue to reject direct SQLite Presentation access, non-Lucide icon families, and raw screen-level HEX colors.
- A post-verification Flet layout defect was corrected: the shared setting row no longer combines `Row.wrap` with an expanded child. Flet 0.84 rendered that invalid flex combination as a large gray rectangle. A structural regression test now rejects the combination.

## Responsive and accessibility behavior

Settings uses one compact 1000-pixel maximum content area on wide desktops and switches to a compact category selector at narrow desktop widths. The resize handler refreshes route content only when the Settings breakpoint changes; it does not remount the shell. Semantic theme focus styling, labeled buttons, tooltips for icon-only actions, explicit reorder controls, contained dialog validation, and existing cancel actions remain available. No hover-only workflow or decorative motion was introduced.

## Verification

Commands executed:

```powershell
cd E:\Projects\Overlord
python -B -m unittest discover -s tests
python -B scripts\smoke_environment.py
git -c safe.directory=E:/Projects/Overlord diff --check
```

The deterministic web demo was historically restarted at `http://127.0.0.1:8550/settings` after the U5 code change. The mounted shell, selected Settings route, categorized wide layout, narrow-breakpoint behavior, and lack of a global Loading state were inspected at that time. Web mode was later retired because Flet's single `flutter-view` prevents useful block-level Codex browser annotations; this paragraph remains historical verification evidence, not a supported launch instruction. Automated tests exercise theme/startup/sidebar persistence, duplicate-route and delayed-loading behavior, dialog validation, standalone and Project-scoped Quick Task flows, transient Cycle creation, deterministic demo isolation, source encoding, and architecture boundaries.

The in-app Flet canvas capture is tiled and masks some interactive controls as gray surfaces, so it is not reliable for pixel-level contrast, focus-ring, Windows scaling, or all-screen screenshot comparison. A physical desktop review across every requested viewport/theme/scale combination was not claimed. Those visual judgments belong in the next manual redesign pass.

## Remaining limits

The permanent Task Detail container, real logo/Windows icon, decorative animation direction, and final category-specific visual polish remain approval gates. Python 3.14/Flet import and integration-test startup can still be slow on this Windows environment even though route queries are fast and do not flash global loading.

Recommended next phase: `Manual Product & UX/UI Redesign Pass`.
