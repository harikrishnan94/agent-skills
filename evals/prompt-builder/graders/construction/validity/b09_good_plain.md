You are writing the migration guide for our REST API going from v1 to v2, aimed at outside developers who integrate with us. The breaking changes are listed in CHANGELOG-v2.md, and the API definitions live at openapi/v1.yaml and openapi/v2.yaml. The guide goes under docs/migration/.

I am available and want to see drafts — show me the outline and the first section early. If a changelog line is confusing, ask me instead of interpreting it loosely.

Before you start, write down what you expect the finished guide to cover: every breaking change from the changelog, each with a working before-and-after example. Check that expectation against the changelog itself, and if a mismatch shows up mid-draft, bring it to me.

Every statement in the guide has to be checked against the spec files, not written from memory — endpoint paths, field names, status codes, all of it. Each before-and-after example must be traced back to the exact place in the spec that justifies it. Nothing goes in the guide on trust.

Stay inside docs/migration/ — do not restructure the API or edit the spec files, and leave everything outside that directory untouched.

The examples have to really work, not just read well: run scripts/validate_examples.py over the guide and it must pass with every example green before you consider the guide done.

When the draft is finished, hand it to a completely separate fresh session that did not write any of it and have it play a skeptical outside developer: follow every step literally and try to prove the guide wrong — wrong field names, examples that do not run, steps that quietly assume knowledge the reader will not have. Fix whatever it turns up.

If you cannot pin some breaking change down from the specs, tell me, and mark it plainly in the guide as an open question rather than inventing an example that merely looks right.
