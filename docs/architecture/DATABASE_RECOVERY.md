# Database Migration and Recovery

At startup Overlord recognizes an empty database, the exact legacy Project/Task schema, or a database with a valid migration ledger. Unknown legacy shapes and altered migration checksums fail closed.

Before a pending migration batch, Overlord uses SQLite's backup API to create `data/backups/overlord-v{version}-{timestamp}.db`. A JSON manifest records source/backup hashes, sizes, and schema versions. The backup must pass `integrity_check` and `foreign_key_check` before migration begins.

Each migration is immutable and applied transactionally where SQLite permits. Failure rolls back the active version. There are no automatic reverse migrations.

If startup cannot safely migrate, the normal write UI is not mounted. The recovery screen reports an error identifier and backup location. Restore is an explicit operator action: preserve the failed database under a distinct name, validate the selected backup, then restore it while the app is closed.
