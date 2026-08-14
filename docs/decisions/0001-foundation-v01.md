# Decision 0001 — Foundation v0.1

- Status: Accepted
- Date: 2026-08-06

Retain Python, Flet, and SQLite and evolve the product as a modular monolith. Foundation v0.1 includes baseline safety, the application shell, Dashboard, Project/Task workflows, Settings, and 12-week Cycle foundations. Work Sessions, Weekly Reviews, widget process, habits, skills, analytics, export, and AI remain deferred.

Daily capacity was originally three Primary and four Secondary slots. That daily-planning decision is superseded by Decision 0003; Definition of Done remains required for Milestone assignment. Execution Score is completed originally planned tasks divided by originally planned tasks. The Task editor content is reusable; its permanent page/dialog/panel container remains undecided. Missing brand and animation references use text/static fallbacks only.

UX Phase U2 confirms that Project is optional for Tasks. Standalone Tasks use `project_id = NULL`; artificial fallback Projects are prohibited. Its TaskPlan and Primary/Secondary decisions are historical and superseded by Decision 0003.

UX Phase U3 treats Projects as working contexts rather than CRUD containers. Project progress is Task-based only when eligible Tasks exist; cancelled and archived Tasks do not enter the denominator. Next Action is surfaced only from an unambiguous open-Task source. Project creation is transient, list filters persist, and Project-scoped Quick Task reuses the shared U2 component with Project preselection.

UX Phase U4 treats Cycles as temporary execution periods rather than Project containers. Cycle progress is achieved persisted Weekly Outcomes divided by all persisted Weekly Outcomes; partial, not-achieved, and unplanned weeks remain explicit. The five-step wizard persists nothing before final submission, and final creation is atomic. An existing active Cycle is never silently replaced.

UX Phase U5 closes Foundation with Presentation-only hardening. Settings uses Appearance, Planning, and Startup categories and does not advertise unfinished modules. The mounted shell, approved U1-U4 information architecture, Crimson Focus palettes, and Lucide-only icon rule remain unchanged. Visible English copy is centralized where practical, routine success feedback is non-blocking, and technical exceptions remain in logs rather than user-facing content.

After U5, the optional web preview was retired. Its intended benefit was block-level review through Codex browser annotations, but Flet exposes the UI as one `flutter-view`, causing whole-screen selection instead of useful component targeting. Desktop is the only supported product surface; historical browser checks remain test evidence only.

On 2026-08-11, English/Russian interface localization was approved. Language is a persistent device setting with English as the migration default. A compact EN/RU switch lives in the mounted Sidebar and rerenders the current route without restarting or remounting the shell. User-entered titles, descriptions, and other content are never translated automatically.
