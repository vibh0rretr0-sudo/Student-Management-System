# scripts — setup & utility commands

- `setup_db.py` — creates the `sms` database, the least-privilege `sms_app` user, applies `schema.sql`, then `seed.sql` (if present). Root credentials are prompted interactively, never stored.
- `build_cpp.py` — compiles `cpp_module/src/sms_engine.cpp` to `cpp_module/build/sms_engine(.exe)`.
