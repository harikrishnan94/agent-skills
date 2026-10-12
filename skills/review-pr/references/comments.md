# Review comments

Voice comes from `hari-voice`, sentences from `plain-prose`, AI tells from
`humanize`. These rules are specific to review comments and win where they
differ from `hari-voice`.

## Rules

- An inline comment reads like a quick note to a peer. Lowercase starts and
  fragments are fine, as are "pls", "nit:" and "isn't it?". Most are two to
  four sentences and under about 80 words, unless they need a `suggestion`
  block or a list of sizes.
- One ask per comment. Give the reason, then ask as a question ("can we
  ...?", "could you ...?").
- Leave out line numbers, SHAs, diff stats, internal call chains, and
  reasoning already settled in chat.
- Hedge only what you have not proven: "traced it, haven't run a repro".
- Say when something predates the PR.
- Do not explain basics to an experienced contributor.
- If Hari calls a draft "polished", "AI" or not "lazy" enough, rewrite it
  shorter and looser with the same facts.

## By author

- **Human:** the body opens with "Thanks for the PR, @<handle>!" and one line,
  such as "few comments inline." or "Requesting changes, details inline. Main
  blocker is <X>."
- **AI agent account** (for example `groeneai`): no greeting. Write
  "@groeneai can you ...", one task per paragraph.
- **Test-only bot PR:** "Test only changes.\nLGTM." if it is correct;
  otherwise one direct comment saying what to replace.

## Placement

- One review. Code points go inline on the exact changed line. A point about
  a file outside the diff goes on the nearest related changed line and names
  the file.
- The body names the main blocker in one line; the details go inline.
- A performance-evidence ask goes inline on the hot path. Description and
  changelog asks go in the body as `1) 2) 3)`.
- Replies go in the existing thread. Approval is the review event, not a
  word in a comment.

## Examples Hari posted

> strings don't get anything from the split, isn't it? String column isn't
> fixed size, and with 2 keys (UInt8 + String) `chooseMethod` can't pick
> `key_string`, so it ends up in `hashed` anyway, same as the tuple today.
>
> I'd drop String and keep FixedString (that one does pack):
> ```suggestion
>     return value_type->isValueRepresentedByNumber() || isFixedString(value_type);
> ```
> or add a Nullable(String) query to the perf test to show it's not slower.

> only the probe counter is checked here and the output goes to FORMAT Null,
> so a wrong result would still pass. pls also compare count() and
> sum(cityHash64(l.n, r.n)) with the same query at default
> max_joined_block_size_rows

> The fixed 5x reuse gate predates this PR. Since this changes the gather
> costs, would it be worth revisiting that decision here?

## Posting

1. Re-read the head SHA. If it moved, re-check every anchor and finding and
   tell Hari before posting.
2. Post one review with `gh api repos/<R>/pulls/<N>/reviews --method POST
   --input review.json`. The JSON has `commit_id`, an `event` (`COMMENT`,
   `APPROVE` or `REQUEST_CHANGES`), a `body`, and `comments` entries of the
   form `{path, line, side: "RIGHT"}`, plus `start_line` for a range. Each
   anchor must be a line inside a diff hunk.
3. Read the review back, check each anchor, and give Hari the URL.
4. Edit posted text in place: `PATCH pulls/comments/<id>` for an inline
   comment, `PUT pulls/<N>/reviews/<id>` for the body.
