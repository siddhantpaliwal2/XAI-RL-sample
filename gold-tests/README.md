# Gold-test layout

Every task has one matching directory under `gold-tests/`:

```text
gold-tests/<task-id>/
```

That directory contains the readable source of every file injected by the
task's hidden-test patch. Suites that need mocks or compatibility classes keep
those supporting files under `stubs/` inside the same task directory.

Run `python3 harness/audit_gold_tests.py` to verify task-folder coverage and
confirm that the readable files exactly match the hidden-test patch embedded in
each task package.
