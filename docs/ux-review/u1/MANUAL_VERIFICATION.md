# UX Phase U1 Manual Verification

> **Historical U1 record — partially superseded.** Desktop/demo launch and the visual accessibility matrix remain useful. All Daily Planning, Primary/Secondary assignment, `Plan the day`, and `/planning/day` instructions below describe the retired U1 workflow and are not current product instructions. Current planning verification belongs to the Dashboard three-day board and the Tasks Kanban/week/month workspace.

## Why the screenshot matrix is manual

The populated Dashboard was historically inspected in the Codex in-app browser, but Flet exposes the application as one `flutter-view` surface. Browser annotation and capture cannot reliably target individual Overlord controls and repeated the rendered surface in screenshots. Web mode is now retired, so the supported visual matrix is desktop-only.

No screenshot files are claimed as validated evidence. Use the steps below to complete the visual matrix without touching production data.

## Reset the deterministic demo

From `E:\Projects\Overlord`:

```powershell
python scripts/seed_demo.py
```

The demo database is `E:\Projects\Overlord\data\demo\overlord_demo.db`. The command never seeds `data\overlord.db`.

## Desktop launch

```powershell
python main.py --demo
```

There is no supported web launch. `python main.py --web` and port arguments are rejected intentionally.

## States to inspect

- Populated demo Dashboard: `/dashboard`
- Unified empty state: `/dashboard?date=2026-09-30`
- Historical only — retired Daily Planning: **Plan the day** and `/planning/day?date=2026-08-06` no longer exist.

## Required matrix

For each viewport, the original U1 matrix inspected the populated Dashboard, empty Dashboard, and the now-retired Daily Planning screen. Current verification should inspect the Dashboard and Tasks Kanban/week/month workspace instead.

| Viewport | Theme | Sidebar | Motion |
|---|---|---|---|
| 1024x720 | Light and Dark | Expanded and collapsed | Normal and reduced |
| 1280x720 | Light and Dark | Expanded and collapsed | Normal and reduced |
| 1600x900 | Light and Dark | Expanded and collapsed | Normal and reduced |

Verify:

- Today’s Tasks remains dominant and does not show empty slot controls.
- Current Cycle and Weekly Progress remain compact supporting cards.
- Needs Attention appears only when actionable items exist.
- At narrower widths, the supporting column stacks without clipping controls.
- Historical acceptance only: the former empty-state **Plan the day** action and Daily Planning assignment controls were removed by the approved date-driven Tasks decision.
- Light/Dark use Crimson Focus tokens; focus, disabled, warning, blocker, and completion states remain legible.
- Collapsed navigation keeps tooltips and keyboard-focusable targets.
- Reduced motion removes nonessential animation.

Save any manually captured evidence in this directory using names such as `dashboard-1280x720-dark-populated.png` and `dashboard-1024x720-light-empty.png`.
