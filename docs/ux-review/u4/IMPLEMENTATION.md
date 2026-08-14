# UX Phase U4 - 12-Week Planning and Review

Status: implemented on 2026-08-07.

Automated result: 91/91 repository tests passed. The current production database baseline and final SHA-256 are both `CAB5F06039D815C5B19AB7A840F068AE23E6F7BF8D15EF2E9269DFB5786435DE`; integrity check is `ok` with zero foreign-key violations. A user-created Project added through the live production web app at 14:34 was preserved and is included in that baseline.

## Scope

U4 changes only 12-Week Plan browsing, Cycle creation, Cycle Detail, Weekly Outcome editing, and Cycle lifecycle presentation. U1-U3 screens, Domain entities, schema, and migration history remain unchanged.

## Browse-first Cycles

The Cycle list now uses a consolidated summary query rather than querying full Cycle detail per card. Cards show lifecycle, date range, active week, Main Outcome, explicit Weekly Outcome progress, connected Projects, next connected Milestone, and an Open action. Search and lifecycle filters persist in session state.

Weekly Outcome progress uses achieved persisted Weekly Outcomes divided by all persisted Weekly Outcomes. Partial and Not Achieved results are reported separately. Weeks without a persisted Outcome are explicitly unplanned and do not silently expand the denominator.

## Five-step wizard

`/cycles/new` contains exactly five transient steps: Identity, Dates, Connections, Weekly Outcomes, and Review. The wizard creates no database records before final submission. Cancel requires no cleanup.

Final submission uses one Application command and one Unit of Work for the Cycle, selected Projects, existing Milestones, and planned Weekly Outcomes. A simulated outcome-write failure rolls back the entire graph. Create and activate is disabled when another active Cycle exists; no Cycle is silently deactivated.

## Cycle Detail

Cycle Detail prioritizes Main Outcome, Current Week, explicit Weekly Outcome progress, a compact full-week sequence, connected Project context, existing Milestones, participating Task counts, and secondary lifecycle actions. Weekly Outcome editing is focused on one week and does not expose twelve permanent forms.

## Data and performance

No migration was required. The SQLite Cycle summary implementation uses a bounded set of list, aggregate-outcome, Project, and Milestone queries for the full result set, avoiding one full-detail query per Cycle card. Detail composes U3 Project summaries only for connected Projects on the opened Cycle.

Demo seed version 4 includes an active Week-3 Cycle with one unplanned future week, a Draft Cycle, a completed historical Cycle, and an archived Cycle.

## Verification

```powershell
cd E:\Projects\Overlord
python -B -m unittest discover -s tests -v
python -B scripts/smoke_environment.py
python main.py --demo
```

The current U4 build was also reviewed in the Codex in-app browser against the deterministic demo database at the normal desktop viewport. The browse-first list, populated summary cards, first wizard step, active Cycle detail, current-week emphasis, explicit Weekly Outcome denominator, and compact week sequence rendered without a recovery or global Loading state. Chrome was not launched. The remaining light/dark, collapsed-sidebar, and multi-scaling desktop matrix remains a user-operated visual review.
