# Foundation v0.1 Architecture

Overlord is a modular monolith. Presentation depends on Application DTOs and commands; Application owns use-case and transaction boundaries; Domain owns entities and rules; Infrastructure implements SQLite ports.

```text
Flet Presentation → Application → Domain
                         ↑
                  SQLite Infrastructure
```

Connections are created per command/query, enable foreign keys and a bounded busy timeout, and close through context managers. Commands use one explicit Unit of Work; repositories never commit. Queries return immutable read models rather than SQLite rows.

The Dashboard is a composed query, never an entity or table. Task planning is append-only. Blocked state is derived from an open Blocker. Cycle relationships use junction tables so Projects and Tasks remain independent across cycles.

The stable startup command remains `python main.py`. `overlord/bootstrap.py` is the composition root. A future widget may reuse Application queries through a separate read-only connection, but no widget process is part of v0.1.
