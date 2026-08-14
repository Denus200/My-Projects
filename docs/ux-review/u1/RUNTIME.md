# UX Phase U1 Runtime Guide

Open and run the repository directly from `E:\Projects\Overlord`.

## Production desktop

```powershell
Remove-Item Env:OVERLORD_DEMO -ErrorAction SilentlyContinue
python main.py
```

Database: `E:\Projects\Overlord\data\overlord.db`

Normal mode never invokes the demo seed.

## Demo desktop

```powershell
python main.py --demo
```

Database: `E:\Projects\Overlord\data\demo\overlord_demo.db`

## Retired web mode

The U1 web preview was an experiment for reviewing Overlord through Codex's browser annotation workflow. Flet renders the interface as one `flutter-view` surface, so the annotation system selects the entire application instead of individual Overlord controls. The workflow did not provide useful block-level feedback and added browser/runtime complexity.

Web mode is therefore retired. `main.py` rejects `--web` and `--port` before Flet starts or a database is opened. Use desktop or demo desktop only. Historical web verification in older reports remains evidence of what was tested at the time, not a supported launch path.

Startup stores a seed-version, date, and semantic fingerprint beside the disposable demo database. Task changes remain visible for the current demo process, but they intentionally invalidate that fingerprint: the next demo process reseeds the disposable database instead of treating those changes as durable user data. A second demo desktop process reuses the database only when the manifest still matches. The explicit `python scripts/seed_demo.py` reset deletes the disposable database, so stop active demo desktop processes before running that maintenance command on Windows.

## Development diagnostics

Source launches use development diagnostics by default. `data/logs/overlord.log` is used for production mode and `data/demo/logs/overlord.log` for demo mode.

Startup entries include:

- `mode=production|demo`;
- `application_type=desktop`;
- absolute `database=` path;
- `demo_seed=reset|not_applicable`;
- seed completion timestamp and elapsed milliseconds.

Route entries include requested and previous routes, query start/completion, content render completion, total milliseconds, failure state, and whether the delayed content progress bar became visible.

Disable route timing logs for a production-like source run:

```powershell
$env:OVERLORD_ENV = "production"
python main.py
```

## Navigation lifecycle

The root shell is mounted once per Flet session. Route changes immediately update navigation selection, query and build only the content region, and keep the previous content visible during fast transitions. A content progress bar appears only after 150 ms and is cancelled when the route finishes sooner. Duplicate active or pending routes are ignored, and route failures replace only the content region with a contained retry state.
