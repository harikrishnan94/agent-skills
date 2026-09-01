---
name: plain-prose
description: >-
  Make prose a reader understands in one pass, including a reader who does not
  read English as a first language. Use whenever drafting or cleaning up text a
  person will read — a commit message, a PR description or review reply, a
  GitHub or Jira comment, a Slack message, an email, a design doc, a README, a
  code comment — and on cues like "this is hard to follow", "too dense",
  "simplify the wording", "make this readable", "explain it plainly", or "I had
  to read that twice". Shortens the distance between words that depend on each
  other, puts the new point where the reader expects it, replaces a team's
  private vocabulary with the thing it names, and keeps every fact: it
  simplifies the sentence, never the content. Not about voice, tone, or
  personality, and not about code-level review tells.
---

# Plain prose: understood in one pass

The bar: the reader gets it the first time, at reading speed, without going
back to the start of the sentence. Many of your readers do not read English as
a first language, and none of them owe you a second pass.

A sentence a reader has to parse twice is a defect. The writer saved a minute
and charged it to every reader.

**Plain does not mean shorter, and never means vaguer.** A good rewrite is
often longer than the original and says strictly more. Simplify the sentence,
never the content.

## The rules

Each rule is a test you can apply to a sentence without knowing the subject
matter. The numbers come from published standards and studies — see the last
section.

1. **One idea per sentence.** Cap a sentence that tells someone to do something
   at 20 words, and a sentence that describes something at 25. One topic per
   paragraph, at most six sentences.
2. **Keep words close to the words they depend on.** Reading cost comes from
   the *distance* between a word and the word it belongs to, not from length by
   itself. Keep the subject next to its verb, the verb next to its object, the
   modifier next to what it modifies. Never split a subject from its verb with
   a clause. A long, straight sentence reads easily; a short, tangled one does
   not.
3. **Start with what the reader already knows. End on the new point.** The end
   of a sentence is where the reader puts the emphasis, so the news belongs
   there — as the main clause. A point delivered in a trailing `..., which is
   what ...` sits in the weakest position in the sentence. Cut the clause and
   make it the next sentence.
4. **Budget one unfamiliar term per 50 words.** A reader needs to know about 98
   percent of the words to follow a text without help. That is one new term per
   two or three lines. Past that the text becomes a wall, whatever its sentence
   length.
5. **Delete your team's private vocabulary.** An invented word for a data
   layout, an in-house abbreviation, a metaphor left over from the design
   discussion — the reader has none of it. Write what the thing *is*. Defining
   the term in place does not repair the damage. An unfamiliar term slows the
   reader down and pushes them to give up, on top of whatever they fail to
   understand. Keep a term only when it is the field's shared name and no
   ordinary words replace it.
6. **No noun stack longer than three words.** Four or more nouns in a row is a
   compressed sentence. Unpack it into words with a verb in them.
7. **Name the actor and use the active voice.** "The platform team picks the
   date" beats "a date will be picked". Passive is for when nobody knows the
   actor.
8. **Take the short word.** *use* not *utilize*, *so* not *thereby*, *lets*
   not *is what enables*, *before* not *prior to*, *about* not *with respect
   to*. The long word buys no credibility — readers rate hard-to-read writing
   as coming from a *less* able author.
9. **Say what the text is for in the first two sentences.** In a message to a
   person, that means the ask and who owns it.
10. **Keep every fact.** Plain is not vague. Every number, caveat and
    condition in the original survives the rewrite.

## Examples

The subject matter in these is irrelevant, and deliberately different in each.
What transfers is the move, not the words.

A trailing clause and a noun stack (rule 3, rule 6):

```text
before: The rollout is paused because the canary error budget consumption rate
        exceeded the threshold set for the deploy freeze window, which is why
        nothing shipped today.
after:  The canary used up its error budget too fast, so the rollout paused.
        Nothing shipped today.
```

Private vocabulary (rule 5), plus one idea per sentence (rule 1):

```text
before: The fanout path now resolves through the slot table instead of walking
        the shard ring, so tail latency drops.
after:  A write goes to several replicas. The code used to check the shards one
        by one; now it looks each replica up in a table. The slowest writes get
        faster.
```

A buried actor and a nominalization (rule 7, rule 8):

```text
before: It was determined that a decision regarding the migration timeline will
        be required from the platform team prior to the freeze.
after:  The platform team needs to pick a migration date. Please decide before
        the freeze starts on Friday.
```

In all three the facts survive and the terms that name real, shared things stay
(canary, error budget, replica, shard, freeze). What goes is the invented
naming, the stacked nouns, the trailing point, and the missing actor.

## Rewriting text you did not write

Keep every fact, every number, every caveat. A rewrite that reads well and
means something else is worse than the tangled original. Where you cannot tell
what a sentence means, ask the author — do not guess, and do not quietly drop
the sentence.

## The check

Read the finished text once, at normal speed. Mark every sentence you went back
into. Those are the ones to fix — usually by moving a word closer to what it
depends on, or by cutting a trailing clause loose.

Do not use a readability score as the gate. Those formulas count word length
and sentence length, and nothing else. They rate nonsense as highly readable,
and they move several grades if you only add full stops. They cannot see rule
2, rule 4, or rule 5.

## Two things this skill is not

- **Not voice.** Tone, warmth, greeting, how you sound — a voice or
  house-style skill owns that, and it outranks this one on wording wherever the
  two disagree.
- **Not dumbing down.** No glossary, no summary section nobody asked for, no
  explaining what the reader already knows. The reader is not slow. They are
  busy, and they may be reading in their third language.

## Where the numbers come from

- 20/25 words per sentence, one topic per paragraph, six sentences per
  paragraph, three-word noun clusters, active voice, one instruction per
  sentence: [ASD-STE100 Simplified Technical
  English](https://www.asd-ste100.org/), the controlled-language standard for
  aerospace documentation read worldwide by non-native speakers.
- Distance, not length, drives difficulty: Gibson's [dependency locality
  theory](https://tedlab.mit.edu/tedlab_website/researchpapers/Gibson_2000_DLT.pdf),
  and Temperley's finding that written English already minimizes dependency
  length.
- Known information first, new point at the end: Gopen and Swan, [The Science
  of Scientific
  Writing](https://www.usenix.org/sites/default/files/gopen_and_swan_science_of_scientific_writing.pdf)
  (topic position and stress position).
- 98 percent known words for unassisted reading: Hu and Nation (2000), and
  Nation (2006) on the vocabulary size that reaches it.
- Jargon costs fluency and engagement, and defining it does not fully repair
  the loss: [Bullock et al.
  2019](https://journals.sagepub.com/doi/abs/10.1177/0963662519865687) and
  Shulman et al. 2020.
- Long words lower judged ability: [Oppenheimer
  2006](https://onlinelibrary.wiley.com/doi/10.1002/acp.1178).
- Readability formulas are poor gates: [Formulas, systems and LLMs are poor
  predictors of reading ease](https://arxiv.org/abs/2502.11150), plus the
  classic critiques of Flesch-Kincaid.
