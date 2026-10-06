# Legacy portal snapshot

This branch records the live legacy library at `2026-10-05T14:21:26.974950+00:00`.
It is an exact asset and catalog snapshot, not a validated KiCad release or a
designer clone target. The portal remains authoritative until a separate
reviewed migration is complete.

- Asset files: 62,112 (5,071,099,474 bytes), under `snapshot/assets/` with their
  original `/data`-relative paths.
- Part catalog rows: 97,978; sources:
  13. `snapshot/inventory.json` preserves
  each row's status, references, provenance, and approval fields, plus every
  asset SHA-256.
- Inventory report SHA-256: `e1a1a1254014074a516063e990501197247c681389ba8d310a88b36667673ad5`.
- Inventory file SHA-256: `21c2b298d0123029b78a3382de799752bc2bbbf774bd6e732c2c3c16cdce90c1`.

`snapshot/assets/staging/` is retained as staging evidence. Those files are not
accepted parts and must be reviewed before entering a designer-facing library.
The snapshot preserves existing reference errors and catalog gaps; it does not
repair or silently omit them. The source export script is included here for
reproduction. Do not commit credentials or the full Postgres database dump.
