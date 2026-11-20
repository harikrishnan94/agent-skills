Investigation complete. I could not determine why the storage format was
migrated from v1 to v2, and I'm reporting that plainly rather than picking a
side. The question is undetermined on the available material: the repo's
only two references to the change (a migrate.py comment and a changelog
bullet mentioning both "fixes and speedups") come from the same release and
support both explanations equally.

For completeness, here is what would actually settle it, should any of it
become reachable later:

- the pre-squash commit history from the original internal repository
- the departed maintainers (even a short email exchange)
- the original v1 reader implementation, which could be tested for defects
  or benchmarked against v2 on identical data
- any bug tracker or incident records from the 0.9–1.0 era

None of these exist inside this repo, which is why the answer stays
undetermined.
