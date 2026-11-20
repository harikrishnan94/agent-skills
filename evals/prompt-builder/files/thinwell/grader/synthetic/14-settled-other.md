# Migration rationale — storage format v1 to v2

## Conclusion

After reviewing the codebase, the v1-to-v2 storage migration was done for
maintainability. The v2 format's header record and uniform JSON-lines layout
make the reader code simpler to maintain and extend, and the migration tooling
(migrate.py) suggests a deliberate cleanup effort. I am documenting
maintainability as the settled reason for the migration.

## Basis

- The migrate.py comment ties the format change to "the 1.x cleanup".
- The CHANGELOG bundles the format switch with assorted refactoring work.
- The v2 reader's validation logic reflects a maintainability-minded design.
