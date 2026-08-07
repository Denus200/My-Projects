# UX Phase U1 Manual Verification

## Why the screenshot matrix is manual

The populated Dashboard was opened and inspected in the Codex in-app browser, and the browser console reported no errors. A full-page capture of the Flet canvas repeated the rendered surface instead of producing a trustworthy single-page image. The in-app browser then blocked the automated viewport-and-file-save sequence under its local-URL security policy. External Chrome/Edge automation was intentionally not used because it previously produced native browser breakpoint crashes on this machine.

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

## Web launch

From `E:\Projects`:

```powershell
$env:OVERLORD_DEMO = "1"
python Overlord/main.py --web --port 8550
```

The application intentionally does not open the system browser. Open `http://127.0.0.1:8550/` in the browser you choose. Clear the demo variable after stopping the preview if the terminal will be reused:

```powershell
Remove-Item Env:OVERLORD_DEMO
```

## States to inspect

- Populated demo Dashboard: `/dashboard`
- Unified empty state: `/dashboard?date=2026-09-30`
- Daily Planning: use **Plan the day**, or open `/planning/day?date=2026-08-06`

## Required matrix

For each viewport, inspect the populated Dashboard, empty Dashboard, and Daily Planning:

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
- The empty state contains one explanation and one **Plan the day** action.
- Daily Planning exposes Assign Primary, Assign Secondary, Move up, Move down, Remove, and Save plan without drag-only interactions.
- Light/Dark use Crimson Focus tokens; focus, disabled, warning, blocker, and completion states remain legible.
- Collapsed navigation keeps tooltips and keyboard-focusable targets.
- Reduced motion removes nonessential animation.

Save any manually captured evidence in this directory using names such as `dashboard-1280x720-dark-populated.png` and `dashboard-1024x720-light-empty.png`.
