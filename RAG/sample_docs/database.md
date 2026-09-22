# Database conventions

## Sessions
Always use the `session_scope()` context manager. Never call `session.commit()` manually
inside a helper; the scope commits or rolls back.

## Migrations
Schema changes require an Alembic migration with a reversible `downgrade()`.
Never edit an already-merged migration.
