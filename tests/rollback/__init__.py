"""
Neo Agent rollback verification tests package.

Stage E.4: Automated rollback verification scripts.

These tests verify the integrity of the Web <-> Tkinter rollback procedure
documented in ``docs/rollback-procedure.md``:

- ``test_rollback_procedure.py``: launch mode dispatch
  (main.py imports, _run_tkinter, ENABLE_WEB_GUI env var, shared db path).
- ``test_db_consistency.py``: shared SQLite database
  (WAL mode enabled, two DatabaseManager instances coexist without conflict).

All tests gracefully skip themselves when optional runtime dependencies
(``tkinter`` for Tkinter mode, ``fastapi`` for Web mode) are missing,
allowing ``python -m unittest tests.rollback`` to succeed on minimal envs.
"""
