# GitHub activity discovery

Collect independently of Notion and sessions. Discover across every repository
visible to the authenticated account, including private repositories. Narrow
to #dev-relevant work only after discovery. An issue or PR need not be authored
by Hari for his contribution to qualify.

## Identity and access

Resolve the authenticated user with the GitHub connector or `gh api user`;
Hari's expected login is `harikrishnan94`, but verify it. Do not substitute
public-only activity for authenticated private access. Check access to the
known ClickHouse public and private repositories and record any failures.
Never expose tokens or copy credentials between hosts.

## Collect complementary sources

Use available read-only connectors or authenticated `gh api`. Start with all
activity types, then inspect action details; an events feed alone is not a
complete history.

1. Page the authenticated user's activity feed (`GET /users/{login}/events`).
   Keep original event IDs, actors, timestamps, repository and payload links.
   This covers pushes, PR and issue events, reviews/comments, branch/tag
   creation or deletion, releases, forks, stars and other recorded actions.
2. Independently search updated issues and PRs with `involves:LOGIN`, and PRs
   with `reviewed-by:LOGIN`. Also search `author:LOGIN` and `commenter:LOGIN`
   when needed to check coverage or split a capped result set. Use the UTC
   calendar day containing the cutoff as the broad lower bound; apply the
   exact `(posted_at, collected_at]` boundary to the returned actions.
3. Search commits by authenticated author/committer and date across visible
   repositories. Resolve commits in push payloads or known active branches
   directly too: search may not include unmerged branch commits. Account for
   commits by collaborators separately; a commit pushed by Hari is not
   necessarily authored by him, and a merge by someone else is not his merge.
4. Check authored/commented GitHub Discussions and other activity surfaced by
   the feed. Work discovered there still needs a corresponding issue or PR
   before entering the #dev draft. Do not discard a relevant workstream just
   because its evidence began in a discussion or commit.
5. On candidate issues/PRs, page timeline events, ordinary comments, submitted
   reviews, and inline review comments as needed. Fetch the author and actual
   action timestamp; do not infer review activity from PR `updated_at` or a
   review request. Read edits at their edit timestamp when relevant. Get PR
   commits/associated PRs to connect work to a canonical issue or PR.

Useful REST routes (substitute verified repository names and IDs):

```text
GET /user
GET /users/{login}/events?per_page=100
GET /search/issues?q=involves:LOGIN updated:>=YYYY-MM-DD&per_page=100
GET /search/issues?q=is:pr reviewed-by:LOGIN updated:>=YYYY-MM-DD&per_page=100
GET /search/commits?q=author:LOGIN committer-date:>=YYYY-MM-DD&per_page=100
GET /search/commits?q=committer:LOGIN committer-date:>=YYYY-MM-DD&per_page=100
GET /repos/{owner}/{repo}/issues/{number}/timeline?per_page=100
GET /repos/{owner}/{repo}/issues/{number}/comments?per_page=100
GET /repos/{owner}/{repo}/pulls/{number}/reviews?per_page=100
GET /repos/{owner}/{repo}/pulls/{number}/comments?per_page=100
GET /repos/{owner}/{repo}/pulls/{number}/commits?per_page=100
GET /repos/{owner}/{repo}/commits/{sha}/pulls?per_page=100
```

Supply query parameters as structured tool/CLI arguments, not an unescaped
URL containing spaces. For example, `gh api --method GET search/issues -f
q='involves:LOGIN updated:>=YYYY-MM-DD' -f per_page=100 --paginate`. These are
read operations; do not invoke mutation tools to collect or confirm activity.
Use GraphQL search for Discussions where REST/connector coverage is absent.

## Time, attribution and completeness

Search `updated:` filters an object's last update, not Hari's action time.
Search through the collection time without an upper `updated:` bound: an
object may have been updated again after collection while still containing
in-window activity. Filter its actual events to the fixed interval instead.
For authored objects, verify `created_at`; for reviews, `submitted_at`; for
comments, creation/edit time and author; for merges/closures, timeline actor
and event time. Do not count other people's comments as Hari's work.

GitHub's activity API has retention/count limits and can lag. Search also has
result caps and can omit unindexed/private data. Page until exhausted or the
window is covered; check `total_count`, `incomplete_results`, permissions and
rate limits. Split capped searches by date/repository and deduplicate the
union. Supplement a feed that does not reach the cutoff with searches and
repository timelines. Inspect known active PRs directly for recent activity
instead of treating an empty feed as proof of no work.

A source call returning successfully does not establish full coverage. Keep
a brief record of queries, pages, oldest event, inaccessible repositories and
remaining gaps. Deleted content, inaccessible private work or an interval
outside retained history may prevent full reconstruction. Say what could
not be covered; never quietly label a partial scan "all GitHub activity".

Merge duplicate representations of the same action from feeds, searches,
Notion and sessions. Distinguish merely prepared local drafts from submitted
reviews/comments. Count relevant activity even when no session mentions it.
Preserve the user's issue-or-PR requirement for every final bullet.

Primary API references, checked when this skill was created:
- [Events API](https://docs.github.com/en/rest/activity/events)
- [Issue and PR search](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests)
- [Commit search](https://docs.github.com/en/search-github/searching-on-github/searching-commits)
- [Discussion search](https://docs.github.com/en/search-github/searching-on-github/searching-discussions)
