# UX Phase U1 Runtime Guide

Run these commands from `E:\Projects`.

## Production desktop

```powershell
Remove-Item Env:OVERLORD_DEMO -ErrorAction SilentlyContinue
python Overlord/main.py
```

Database: `E:\Projects\Overlord\data\overlord.db`

Normal mode never invokes the demo seed.

## Demo desktop

```powershell
python Overlord/main.py --demo
```

Database: `E:\Projects\Overlord\data\demo\overlord_demo.db`

## Demo web

```powershell
$env:OVERLORD_DEMO = "1"
flet run --web --port 8552 -r Overlord/main.py
```

Database: `E:\Projects\Overlord\data\demo\overlord_demo.db`

`--demo` and `OVERLORD_DEMO=1` resolve to the same absolute path and run the same deterministic seed preparation before Flet serves the first session. A missing, stale, or modified demo is reset; an already verified canonical seed is reused. Additional web sessions reuse the completed process-level preparation.

Startup stores a seed-version, date, and semantic fingerprint beside the disposable database. A second demo process reuses the database only when that manifest still matches; otherwise startup safely resets it. The explicit `python Overlord/scripts/seed_demo.py` reset deletes the disposable database, so stop active demo desktop/web processes before running that maintenance command on Windows.

When the demo web terminal is reused for production, clear its scoped variable:

```powershell
Remove-Item Env:OVERLORD_DEMO -ErrorAction SilentlyContinue
```

## Development diagnostics

Source launches use development diagnostics by default. `data/logs/overlord.log` is used for production mode and `data/demo/logs/overlord.log` for demo mode.

Startup entries include:

- `mode=production|demo`;
- `application_type=desktop|web`;
- absolute `database=` path;
- `demo_seed=reset|not_applicable`;
- seed completion timestamp and elapsed milliseconds.

Route entries include requested and previous routes, query start/completion, content render completion, total milliseconds, failure state, and whether the delayed content progress bar became visible.

Disable route timing logs for a production-like source run:

```powershell
$env:OVERLORD_ENV = "production"
python Overlord/main.py
```

## Navigation lifecycle

The root shell is mounted once per Flet session. Route changes immediately update navigation selection, query and build only the content region, and keep the previous content visible during fast transitions. A content progress bar appears only after 150 ms and is cancelled when the route finishes sooner. Duplicate active or pending routes are ignored, and route failures replace only the content region with a contained retry state.
