# Per-PR AI cost attribution: what a unit of shipped work cost

Status: **planning; one throwaway reader run, nothing committed**. Last updated 2026-09-05.

A **completed case study**: a replay reader that attributes agent spend to a
branch and a pull request, run over my own history, published with the real
numbers including the share that attributes to nothing.

**The concept in one paragraph.** The harness already meters every call, so
this is a join problem rather than a metering problem, and the join runs
session to branch to pull request. The branch is the hard hop: it is knowable
only at the client, which is why the FinOps vendors stop above it and why this
has to live in the harness. The design that falls out is a replay reader over
persisted session files with the unattributed remainder split by reason rather
than dropped, and the test of whether it works is that per-PR totals plus the
unattributed buckets reconcile against the actual bill. The open question is
whether the numbers are interesting enough to build properly, which is what the
one-evening POC exists to answer.

Deliverables: one project page, one repo, two or three articles, one diagram.

Related briefs: `docs/ideas/becoming-agentic.md` measures what an agent
achieves. This measures what it cost and which unit of work owns it.

Branch `claude/ai-cost-monitoring-portfolio-xd2mqj` on `danieljohnmorris/dan-portfolio`.

**Provenance.** Sections 1 to 9 come from working notes drafted in a separate
conversation. Everything marked *measured 2026-09-05* was run on this machine
in this session, against Claude Code transcripts rather than omp, and either
corroborates or corrects those notes. Both are flagged inline.

---

## 1. The gap

Two layers exist and they have not met.

**FinOps SaaS stops above the pull request.** CloudZero, Vantage, Finout and
Cloudability all ship AI modules; the granularity they advertise is
per-developer, per-team, per-project, per-sprint. Anthropic's Enterprise
Analytics API added per-user attribution in March 2026: named user consumption,
tokens, cost, session counts. None of them join to a branch or a PR. Finout
gestures at "did my PR change spend", but that is the *cloud* cost a PR causes,
not the *agent* cost it consumed.

**Per-PR granularity exists only as OSS side projects.**

| Tool | What it does | Gap |
|---|---|---|
| `receipt` | GitHub Action, itemised cost comment on the PR before merge, per-PR and per-day budgets | Claude Code / Cursor / Copilot / Aider / Codex, no omp |
| `token-pulse` | Local attribution to commits, branches, PRs (`token-pulse pr 1234` via `gh`) | Reads Claude Code logs |
| `CodeLedger` | Per-project, per-agent, per-skill | No PR join |
| `pi-cost` | Overview to project to session to message | Drill-down stops at the session |
| `CodexBar` | Menu bar app, added omp support by scanning session jsonl | Not PR-aware |

**Why the vendors stopped.** AI calls are stateless, so there is no persistent
resource to tag the way FinOps tags infrastructure. Most FinOps teams can
attribute only 40 to 60% of AI spend to a team or product. The branch is
knowable only at the client, which is what puts this in the harness and keeps
the SaaS tier out of it.

### Measured on this machine, 2026-09-05

**Scope, before any of it is read as a result.** These come from a **single
Claude Code session** in a cloud container: about three hours, one transcript
file, no corpus. The workload is research and writing with heavy file reading
and almost no code generation, which is the shape that maximises cache reads, so
the token *mix* below should not be generalised to a coding session. The token
counts are hard data from the file. The dollar conversions depend on the rate
table in section 15, which has not been checked against the published pricing
page. Nothing here has been run over any real history yet; that is what the POC
in section 12 is for.

Four things, all against Claude Code rather than omp, and all reproducible from
section 15.

**The branch field cannot be trusted, in the way the notes predicted.** Claude
Code writes `gitBranch` on every record. In this cloud session 55 of 66 records
say `HEAD` and 11 say nothing, because the session cwd is `/home/user`, a
parent holding four clones rather than a repository. This is the notes' own
rule arriving from a second direction: never silently log a branch called
`HEAD`, and never derive the repo from the session path.

**Naive summing overstates by 2.97x, by a different mechanism than expected.**
The notes' first must-get-right is to diff cumulative usage rather than sum it.
Claude Code's usage is not cumulative, it is per-message, so diffing would be
wrong here. The trap is elsewhere: **the same assistant message is written to
the transcript two or three times.** 60 records carry usage; 23 distinct
`message.id` values sit behind them. Summing the records gives $27.54, summing
distinct messages gives $9.42.

Deduplicated totals for this session, counted mid-session so they grow as it
runs (they moved from $9.42 to $11.20 over three hours of work), priced at Opus 5
rates ($5/$25 per MTok, cache reads 0.1x input, cache writes 2x at the 1-hour
TTL):

| | Tokens | Cost | Share of bill |
|---|---|---|---|
| Cache read | 2,915,266 | $1.46 | 15.5% |
| Cache write, 1h | 699,488 | $6.99 | 74.2% |
| Output | 38,821 | $0.97 | **10.3%** |
| Input | 48 | $0.0002 | 0.0% |
| **Total** | | **$9.42** | |

The generalisation is that summing without deduplication is a per-harness trap
with a per-harness mechanism, and the only way to find yours is to print the
rows and look at them. That is the notes' rule about subagent double-counting,
applied one level up.

**Output is 10.3% of the bill on this session, which is one data point for an
inference in section 13, not a confirmation of it.** The notes reason that
caveman compresses output tokens and that output is a small slice of agentic
spend, marked "inference, not fact". That label was right and stays. One
read-heavy session at 10.3% output is consistent with it and settles nothing: a
code-generation-heavy session is exactly where the share would be highest, and
that is the case not yet measured. The measurement the tool exists to make is
this share across a real corpus of PRs, split by workload.

**Branch-tip ancestry is not evidence of landing.** `git merge-base
--is-ancestor` over `dan-portfolio` reports 109 of 115 branches as never merged.
The PR API says 91 of the last 100 merged. Squash merge writes a new commit.
This is the mechanical reason behind the notes' "attribute to the branch, not
to commits", and it is worth stating as a measurement rather than a principle.

**Pull request granularity is a habit, not a unit.** On 2026-08-27 between
22:16 and 23:02 I opened 12 PRs in `dan-portfolio`; 7 of them (#193 to #197,
#200, #201) edit one article, and #199 merged 3 seconds after opening. Cost per
PR over that window divides one working session by 12. This does not break the
project, but it does mean the headline unit is **cost per branch**, with cost
per PR reported alongside and the PRs-per-branch distribution published so a
reader can see how much of the variance is mine.

---

## 2. A join problem, not a metering problem

The harness already meters. The four keys differ wildly in reliability.

| Key | Availability | Notes |
|---|---|---|
| Conversation | Free | Session id is in the filename and the header |
| Project / repo | Nearly free | Derive from the git **remote**. Watch `/move` and monorepos |
| Branch → PR | **The real work** | Not in the session file. Inferred from cwd plus timestamps |
| Ticket | Weakest | Not in the harness at all. Needs a branch-naming convention |

Honest ordering: conversation and project you have today, PR is about a week of
work to get good enough, ticket depends on a convention adopted first. The
convention exists in my work repositories already (branch names carry a tracker
id prefix), which makes the ticket hop cheap there and absent on the portfolio.

---

## 3. Attribution design

### Branch → PR

Attribute to the **branch**, not to commits, for the reason measured in section
1. Two fixes, ideally both:

1. Capture the branch **per turn** rather than at session start. People switch
   mid-session and that is most of the attribution error.
2. **Worktree-per-task**, so that cwd *is* the branch.

Then branch to PR is one `gh` call.

### Bucket the remainder by reason, as a state rather than a verdict

- `unattributed:main` - exploration on the default branch.
- `unattributed:no-branch` - detached HEAD, bare checkouts. **Terminal.**
- `unattributed:no-pr` - real branch, never opened a PR. Spikes, abandoned work.
- `unattributed:pending` - branch exists, PR not open *yet*. **Re-resolvable.**

`pending` is the important one. Most branch-shaped work resolves to a PR
eventually, just not when the turn ran. Store the branch regardless and let the
reader re-resolve lazily, so attribution improves over time rather than
freezing at capture. Otherwise every PR is systematically undercounted, because
all pre-PR exploration vanishes.

The unattributed total is not noise. **Sum of PRs plus buckets reconciled
against the bill is the only real test of whether the attribution works.** If
`unattributed:main` is 40% of spend, that is a finding rather than a bug.

### Subagents

Subagents tend to work on one thing and the task prompt describes that thing,
so the subagent is a *better* attribution unit than the parent turn and gives
cost-per-task below cost-per-PR. The join is child to parent to branch to PR,
and attribution inherits downward.

**Verify by hand before trusting.** Does the parent's usage already include
child spend? If it does and you also sum child files, every subagent-heavy PR
doubles. Spawn two subagents, compare parent total against parent-plus-children.
This cannot be reasoned out, only observed. Section 1's duplicate-record finding
is the same lesson: the corpus had a 3x error in it that no amount of reasoning
about the format would have surfaced.

**Capture point.** `session_stop` never fires for task or subagent sessions.
Use the parent-side `tool_result` for the task tool, or skip hooks for children
entirely and let the replay reader pick up their files.

### Intra-turn

A parent turn is heterogeneous, a subagent is not. What actually varies within
a turn:

- **Model calls** - own usage per assistant message. The finest real unit, and
  already recorded.
- **Branch** - changes only if a tool call ran `git checkout`. Detectable.
- **Task or topic** - genuinely varies, and only the model knows it.

Do not ask the model to self-label the third. It would be a guess, it would
cost tokens, and it would be wrong on exactly the messy turns where it matters.
Same trap as asking a model for its own token counts.

**Rule: message-level granularity, turn-level attribution keys.** Log per
assistant message with its own usage, stamp with the branch resolved at that
moment, accept that a turn shares one label, and keep the resolution in the
store so a better join can re-attribute later without re-collecting.

Special-case worth making: task spawns are a clean split. "This turn cost £2, of
which £1.60 was the migration subagent" needs no inference.

---

## 4. Data source: replay the session files

Usage is on the **persisted** messages, not only live in memory. omp surfaces
cumulative usage inline on assistant messages, and the session `.jsonl` is the
transcript of those messages. CodexBar added omp cost support purely by scanning
`~/.omp/agent/sessions/**/*.jsonl` with no hooks; the Agent Hub restores
historical usage from persisted-session discovery. Verify field names by
`cat`-ing a real session file before building on any of this.

### Six things that bite on replay

1. **Branching.** Sessions are a JSONL *tree*: each entry has `id` and
   `parentId` and supports in-place branching, so one file can contain abandoned
   paths. Walk the active branch by parent pointer, do not `jq` the whole file.
   (Claude Code has the same shape under `uuid` / `parentUuid`.)
2. **Cumulative usage.** Diff, do not sum. A naive `map(.usage.cost) | add` over
   a long session can overstate by an order of magnitude.
3. **Duplicate records.** *Added 2026-09-05.* Where usage is per-message rather
   than cumulative, the trap inverts: the same message can be persisted several
   times and summing records overstates. Measured at 2.97x on Claude Code, 60
   records against 23 distinct message ids. Establish which of (2) and (3)
   applies to each harness by printing the rows, not by reading the docs.
4. **Subagents are separate files.** Lineage is needed to roll child cost into
   the parent, or every task-heavy PR is undercounted.
5. **`/move` lies.** The session file stays under the old encoded directory when
   cwd changes; only the in-memory header updates. Do not derive the repo from
   the path, derive it from the remote.
6. **`--no-session` leaves nothing.** That spend is unrecoverable.

The sessions root moves under `XDG_DATA_HOME` when set, so resolve it rather
than hardcoding.

**Check by hand:** whether `/compact` rewrites the transcript or appends a
summary. If it rewrites, historical usage lines may be gone from older sessions,
which caps how far back a backfill really reaches.

---

## 5. Storage

**Append-only JSONL as source of truth, SQLite as a rebuildable index.**

`~/.local/share/omp-cost/YYYY-MM.jsonl`, one line per message, monthly files.
Append-only survives a crash mid-turn, tolerates concurrent instances (a single
`O_APPEND` write under 4KB is atomic on Linux and macOS), and is greppable.
SQLite is built by replaying the JSONL: corrupt or schema-changed, delete and
rebuild.

**Do not invert it.** SQLite as the only copy loses history that cannot be
reconstructed. Concurrency matters more than it sounds, because worktree-per-task
is exactly the setup where four agents append at once.

Record shape:

```
{v, ts, session_id, turn, message_id, repo_remote, branch, head_sha,
 worktree, model, in, out, reasoning, cache_read,
 cache_write_5m, cache_write_1h, cost_usd, cost_src}
```

- `repo_remote` rather than path, so worktrees and reclones collapse to one key.
- `message_id` so deduplication is possible at read time. *Added 2026-09-05,
  from section 1.*
- Cache writes split by TTL rather than one column. *Added 2026-09-05:* on this
  session, using one write multiplier understates by 27.8%, and cache writes are
  74.2% of the bill, so this is the single most consequential column in the row.
- `cost_src` flags provider-reported against locally priced, because you need to
  know which numbers you can defend.

**User-level, not repo-level.** A tracked ledger conflicts on every merge, and
checking out an old branch swaps your history out from under you. Repo-level
would have to live in `.git/` via `--git-common-dir`, since a worktree's
`--git-dir` gives `.git/worktrees/<name>` and you would get a ledger per
worktree. User-level survives repo deletion and gives cross-repo rollups.

---

## 6. Worktrees

**Do this first.** It improves everything downstream and makes the cheap
replay-only version nearly as accurate as the extension version, possibly
letting the extension be skipped entirely.

**Gets better.** Sessions are grouped by encoded working directory, so one
worktree per task makes the session directory effectively the branch. The
cwd-to-branch join is done, with no timestamp guessing, and it survives replay
of old sessions.

**Breaks.**

- Ledger location, per section 5.
- **The path is ephemeral.** Delete the worktree after merge and session files
  sit under a directory that no longer exists. Resolve branch and PR *at capture
  time* and store them; do not plan to derive them later from the path.
- **Detached HEAD.** `gh pr checkout`, bisects and CI checkouts give `HEAD` from
  `rev-parse --abbrev-ref`. Fall back to `git branch --show-current`, then the
  worktree name, then bucket. Never silently log a branch called `HEAD`.
  *Measured 2026-09-05:* this is not hypothetical, it is 55 of 66 records in
  this session, and the cause was a non-repo cwd rather than a detached checkout,
  so the fallback chain needs a "cwd is not a repository" arm as well.
- **Bare layouts** (`repo.git` plus siblings) have no main checkout. The remote
  URL still collapses everything, which is why it is the right key.

---

## 7. omp vs pi, and Claude Code

Same bones: omp is a fork of pi (Mario Zechner) and the session format came
along.

**Shared, write once.** Both persist JSONL with a tree structure, `id` plus
`parentId`, in-place branching without new files. The hard part of the reader is
one parser for both. `pigo` claims byte-compatibility with pi's session format
at a pinned version, which is good evidence the format is stable.

**Differs.**

- **Paths.** pi → `~/.pi/agent/sessions/`; omp → `~/.omp/agent/sessions/`
  (`XDG_DATA_HOME`-relocatable); Prime Agent → `~/.prime/agent/`. Make the root
  configurable.
- **Subagents.** pi deliberately has none and the README suggests spawning pi
  instances via tmux, so all lineage logic is omp-only. On pi, parallel work is
  separate root sessions and cwd or worktree is the only join.
- **Extension registration.** omp needs an absolute path in the `extensions`
  array of `settings.json`, with no auto-discovery. Similar event vocabulary,
  but do not assume payload parity.

**Worth stealing.** pi's bash tool exposes `PI_SESSION_ID`, `PI_SESSION_FILE`,
`PI_PROVIDER` and `PI_MODEL` to commands it runs, so any git operation the agent
performs can stamp the session id into a commit trailer from inside the shell.
That joins session to commit to PR through git itself with no extension at all.
Check whether omp preserves these; if it does, the plugin becomes optional.

**Claude Code as a second reader.** *Added 2026-09-05.* Every measured figure in
this brief comes from Claude Code transcripts at
`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, which have the same tree
shape (`uuid` / `parentUuid`), per-message rather than cumulative usage, an
`isSidechain` flag for subagent records, and the duplicate-record behaviour in
section 4. Supporting it is not scope creep: `receipt` and `token-pulse` already
target Claude Code, so it is the harness where the tool has competition and
therefore the one that proves the reader is harness-agnostic. Section 11 depends
on that being demonstrably true.

**Verdict:** omp for the harness, per the original notes. But omp ships releases
constantly and event payloads will break, so **build the replay reader first and
treat the extension as optional.**

---

## 8. Optional: harness extension

Only if accuracy demands it. A single `.ts` in `~/.omp/extensions/`, absolute
path in the `extensions` array of `~/.omp/agent/settings.json`. The factory does
registration only; runtime actions at load throw. Work happens in
`pi.on("turn_end", ...)`.

**Scope it to logging only.** No `gh` calls, no PR writes. That would put a
network call in the path of every turn and couple the harness to GitHub auth.
Two pieces, each replaceable.

**Worth adding:** a `/cost` slash command for the current branch. That is the
part used daily, more than any dashboard.

**Gotchas.** It only logs sessions it is loaded into, so headless and CI runs
need the same settings.json. Subagent double-counting per section 3.
`ctx.reload()` is terminal, so do not buffer writes across it, append per turn.
Wrap the handler in try/catch and swallow everything: a cost logger must never
block or fail a turn.

**Do not log via a skill or system message.** The model does not reliably know
its own token counts, so you would pay tokens for a guess. The harness has the
real numbers.

---

## 9. Surfacing it

**The PR description is the dashboard.** For n=1, GitHub already does rendering,
archiving, filtering and search. Zero UI, and the number lands where the decision
gets made. It is also the better artifact for the article: a screenshot of a real
PR with a cost line is instantly legible and obviously real.

Mechanics:

- `gh pr edit --body`, writing into a fenced block between HTML comment markers
  so re-runs replace rather than append. Idempotent from day one.
- Body rather than a sticky comment. Comments notify and get buried.
- Trigger manually (`omp-cost pr`) before hooking `pre-push`. You want to
  disagree with the number a few times first.
- **Print-only until the parser is trusted.** Wrong numbers in repo history are
  a bad first impression of your own tool, and section 1 is the argument for
  this: the first figure I computed here was 3x out.

**Constraint:** the PR must exist before anything can be written to it, but most
spend happens before it does. So the run goes after `gh pr create` and looks
backwards over the whole branch, which is `unattributed:pending` resolving.

The bodies become the store. `gh pr list --json body` gets the numbers back out
for trends, which defers a dashboard indefinitely.

---

## 10. What the project may claim

- Every figure carries its denominator and the method that produced it.
- **Every dollar figure states whether it is billed cost or locally priced**, in
  the same sentence as the number. That is what `cost_src` is for.
- Third-party figures are reports, labelled as such, with the vendor's own
  current number rather than the one in circulation. Section 11 has a live
  example of getting this wrong.
- Anything designed but not run is design, not measured.
- The reconciliation gap against the actual bill is published whatever it is.
- `learnings` carries the negative results, including the parser errors.

## 11. Scope guards

**Nothing about my employer's work appears anywhere.** The corpus is my own
repositories and my own sessions.

- [ ] No repository, branch, ticket or PR identifiers from work. The ticket
      convention in section 2 is described generically and never by its prefix.
- [ ] No spend figures, plan terms or seat counts from work.
- [ ] No transcript excerpts from anything other than my own repositories.
- [ ] The committed corpus is regenerable from my own accounts alone.

Session files carry prompts, file paths and tool arguments. The repo commits
**derived rows only**, and the collector strips content at read time rather than
filtering it later.

---

## 12. POC scope

One question: **do the numbers come out interesting enough to build properly?**

**Cut:** extension, SQLite, ledger schema, storage-location decisions, worktree
migration, team rollups, dashboard.

**Keep:** one script that reads the session files, walks parent pointers, gets
usage right per section 4, resolves cwd to repo and a rough branch, and prints a
table. Read-only, no writes, throwaway. An evening.

**Must get right** (everything else can be sloppy):

1. Get the usage arithmetic right for the harness in hand: diff if cumulative,
   dedupe by message id if not. Print the rows and check before trusting either.
2. Follow the active branch of the tree, skip abandoned paths.
3. Check parent/child double-counting by hand.

**Cheat freely.** Time-window branch attribution is fine; this is order of
magnitude, not pennies. Skip the PR join at first, since branch-level tells you
almost as much. Dump CSV and look at it in a spreadsheet.

**Success:** a per-branch cost table over existing history whose total is in the
same ballpark as the actual bill for the period. If those are wildly apart, fix
the parser before doing anything else.

### POC result, 2026-09-05

A throwaway reader exists (Claude Code only, not committed): walk `parentUuid`
for the active path, dedupe by `message.id`, price with the TTL split, resolve
the repo from the remote, bucket the rest. It has been run over **one session,
its own**, which is enough to exercise the parser and not enough to be a result.
On that session it drops 45 duplicate records, discards 48 records off the
active path, and then splits:

| Bucket | Share of spend | Branch resolved by |
|---|---|---|
| `claude/ai-cost-monitoring-portfolio-xd2mqj` | 63% | replay-time fallback |
| `unattributed:no-branch` | 37% | terminal |

Two findings that change the build order.

**The `git branch --show-current` arm of the resolution chain is capture-time
advice being used at replay time.** A replay reader running it resolves to
whatever is checked out *now*, not what was checked out during the turn. It
happens to be right here because the session is hours old and the branch has not
moved. On a backfill over months of history it is silently wrong, and nothing in
the data says so. Replay-only attribution therefore has a correctness ceiling
that no amount of parser work raises.

**37% of spend is terminally unattributable in a session whose work did land on
a branch**, because the cwd was a non-repo parent holding four clones. That is
the `unattributed:no-branch` bucket behaving as designed. It is one session and
a container-specific cwd layout, so the share means nothing on its own; what it
demonstrates is that the bucket fills from a cause the notes did not list, which
is a cwd that is not a repository at all rather than a detached HEAD.

Both point the same way: **worktree-per-task before anything else.** It converts
the replay-time guess into a capture-time fact and it empties the terminal
bucket, and it does so without an extension.

Then, in order: worktree-per-task (section 6), the branch-per-turn capture, the
PR join and the four buckets, PR-body output, and the extension only if the
buckets say the replay reader is not accurate enough.

---
## 13. The code project

**Repo: `danieljohnmorris/agent-spend`.** Named for the thing measured rather
than the harness that produces it. `omp-cost` was the working name and it is the
wrong one: section 15's ilo comparison only carries if the instrument is
demonstrably harness-agnostic, and a tool named after one harness argues against
itself before anyone reads the method. The CLI is `agent-spend`, so the daily
command reads `agent-spend branches` and `agent-spend pr`.

**Python.** The POC is already Python, the hard part is the parser rather than
the runtime, and `uv tool install` is adequate distribution for a tool whose
audience is people who already run coding agents. A single-binary rewrite is a
distribution optimisation and gets revisited only if the tool is actually
adopted, not before.

**The reader interface is the architecture.** One normalised record type, one
reader per harness, everything downstream harness-blind:

```
agent-spend/
  README.md              what it is, and that it is not a billing system
  prices/anthropic.toml  model x tier x speed x token_class, effective_from
  src/agent_spend/
    record.py            the normalised row (section 5's shape)
    readers/
      base.py            yields records; owns dedupe-or-diff per harness
      claude_code.py     ~/.claude/projects/**/*.jsonl
      omp.py             ~/.omp/agent/sessions/**/*.jsonl
      pi.py              ~/.pi/agent/sessions/**/*.jsonl
    pricing.py           TTL-split, effective-dated, cost_src stamped
    attribute.py         branch chain, the four buckets, pending re-resolution
    store.py             append-only JSONL, SQLite index rebuilt from it
    github.py            branch -> PR. Only reached by the `pr` command
    cli.py               scan | branches | pr | reconcile
  tests/
    fixtures/            one redacted session per harness, committed
```

`readers/base.py` owning the dedupe-or-diff decision is the load-bearing choice.
Section 4 hazards 2 and 3 are opposite corrections and each is a property of a
harness, not of the tool, so the knowledge belongs in the reader and nowhere
else. Everything after `record.py` is then testable without a harness installed.

**Committed fixtures.** One redacted session file per harness in `tests/`, with
a test that asserts the priced total. Without it, a harness format change is
found by a wrong number in a PR body rather than by a failing test, and section
9's "print-only until the parser is trusted" never ends.

### Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | POC | A per-branch table over real history. **Reached in prototype, one session only** |
| M1 | Reader interface, omp reader | The four `cat`-a-file questions in section 16 are answered and both readers pass the same fixture test |
| M2 | Store | `agent-spend scan` writes append-only rows; SQLite rebuilds from them; rerunning is idempotent |
| M3 | Attribution | Branch chain with the not-a-repository arm, four buckets, `pending` re-resolves on a later run |
| M4 | **Reconcile** | `agent-spend reconcile` puts PRs plus buckets against the actual bill for one period, and the gap is explainable |
| M5 | PR output | `agent-spend pr` writes an idempotent fenced block into the PR body |
| M6 | Worktree-per-task | Workflow change, no code. Terminal bucket drops and the branch source moves from `replay` to `capture` |
| M7 | Extension | Only if M6 leaves the buckets too large to publish |

**M4 is a gate, not a milestone.** If the total does not land in the same
ballpark as the bill, nothing downstream is worth building and the parser is
wrong. Nothing is drafted before M4 either, for the same reason: section 1
already produced one 3x parser error, and the whole value of the project is that
its numbers are trustworthy.

M6 before M7 is the order the POC result argues for: worktrees convert the
replay-time branch guess into a capture-time fact without an extension, so the
extension is only worth its maintenance if worktrees leave a gap.

---

## 14. Article angle

**The gap is the hook, not the tool.** "I built a cost tracker" is a hundred
posts. "Here is what months of my own agent spend looks like, broken down by PR"
is one, because nobody publishes real numbers. The unattributed buckets are the
best material in it.

**The caveman hook, with the current figures.** caveman reached 4,000 GitHub
stars in days and is now on 30+ agents via the Agent Skills standard, and a
benchmark then concluded its headline claim was both true and misleading. That
gap between real enthusiasm and contested measurement is the whole space.

Use 65% on prose output and 8.5% on agentic coding, from caveman's own
`HONEST-NUMBERS.md`, the second measured by JetBrains across 86 SkillsBench
tasks. The working notes carried ~75% and 87%; both are retired, and
`65-percent-and-8-percent-same-tool` is the post about finding the withdrawn 75%
on my own documentation site four weeks late. Republishing either repeats
exactly the mistake that post documents.

**The sharper version stays an inference until the corpus exists.** caveman
compresses output tokens, and output was 10.3% of the bill on the one read-heavy
session in section 1, where a 65% cut would move 6.7% of spend. That is one
session of the wrong workload shape: code generation is where the output share
would be highest and it is the case not yet measured. The tool settles it across
real PRs against real invoices, and the post reads whichever way it lands.

**Contacting Julius Brussee:** lead with measurement rather than a pitch, and go
after there are numbers. "I ran your skill across N of my PRs, here is the cost
delta, want to see the method before I publish" is useful to him even if
unflattering, and is a better first contact than proposing collaboration.

### ilo alignment

The tracker is the missing *instrument* for ilo's claim. ilo has token efficiency
as a core design goal with benchmarks behind it, but benchmarks are synthetic:
fixed tasks, measured once, chosen by the claimant. Per-PR cost from real work is
the field version. "The same feature cost £X in TypeScript and £Y in ilo across N
real PRs" is hard to wave away, and nobody else has both halves.

Careful about:

- **You built both.** Fix method and metric before looking at data, and publish
  the runs where ilo lost.
- **Confounds swamp n=1.** Task difficulty, model choice and your own ilo
  learning curve all move cost more than the language does.
- **The tracker must be demonstrably harness- and language-agnostic**, which is
  why section 13 names the repo the way it does and keeps three readers.
- **Disclose the ilo work** up front in any caveman piece.

---

## 15. Where this lives on the site

Three artifacts want homes: the tool, the attribution findings, and two
measurements that use the tool on other people's claims. They do not all belong
in the same place, and the temptation is to put them there because it makes the
new project look bigger.

### The project page: new, and small

**A new case study, `agent-spend`.** Full auto-rendered narrative,
`status: 'completed'`, no `simpleView`, `featured: false`, `year: 2026`. It has a
problem, a build, a gate it either passed or failed, and negative results, which
is what the case-study format is for. `site-blocker` is the precedent for
`completed` on a tool still in daily use.

Working title: **What a Pull Request Costs**.

Rejected: a third living map. `token-efficiency` and `agent-skills-and-mcp`
already carry that format and a third would dilute what "map" signals on this
site. This project finishes.

`impact.metrics` carries the reconciliation gap from M4, the four bucket shares,
and the corpus size, each label naming its denominator. `learnings` carries the
parser errors, including the 3x one.

**Boundary sentence, on the page:** `token-efficiency` measures where an agent's
tokens go and is edited in place; this measures which unit of shipped work owns
the spend, and finishes.

### The posts: one here, two feeding existing maps

`project` is a single string on a writing post, so each post lands in exactly one
place. The allocation follows the subject, not the project that produced it.

| Post | Thesis | `project` | Why there |
|---|---|---|---|
| The tracker and the numbers | The join, the four buckets, real per-branch spend, what does not attribute | `agent-spend` | The subject is the attribution problem, which is this project |
| Measuring caveman against a real bill | Output as a share of real spend; 65% applied to actual PRs | `token-efficiency` | It updates a figure already on that map, next to the withdrawn-75% story. Splitting the caveman thread across two pages would make both worse |
| ilo against TypeScript, per PR | The field version of a synthetic benchmark | `ilo-lang` | It is ilo's benchmark, measured differently. The tracker is the instrument, not the subject |

The consequence is deliberate: **the new project page carries one post and stays
small**, and the two maps get updated in place with figures the tracker produced.
That is the living-map pattern working as intended rather than a new page
absorbing everything it touches.

Cross-links do the rest. The tracker page references the caveman and ilo posts in
its Approach prose; both maps link back to the tracker page as the instrument.
`ProjectWritingList` is not needed on the tracker page at one post, matching how
the other case studies are laid out.

### Sequencing

1. M4 passes. Nothing is written before this.
2. Post 1 publishes, with the tracker repo public.
3. The `agent-spend` project page goes up a few days later, so it reads as the
   arrival rather than the announcement.
4. Post 2, plus an in-place edit to `token-efficiency` carrying the new caveman
   figure with its denominator.
5. Post 3, plus an in-place edit to `ilo-lang`.

Scheduling: latest `publishDate` in the collection is currently 2026-08-31; check
at draft time and schedule one per day from the day after the last scheduled
post, leaving a gap before the project page. Both gates on every draft: `bash
scripts/writing-check.sh` and the `write-as-dan` pass, with three specific
considered phrases reported before the draft is shown.

**Tags** for all three, from the existing vocabulary: `llm`, `tooling`,
`agents`, plus `claude-code` on post 1 and `ilo` on post 3. No new tag is
introduced for cost; `tooling` already covers it and a one-post tag makes the
tag pages worse.

---

## 16. Open questions and verification

Measured here on 2026-09-05, reproducible:

- Session totals and the duplicate-record factor: read
  `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, collect records where
  `message.usage` exists, compare the raw count against distinct `message.id`,
  and sum both.
- `gitBranch` distribution: count the key across all records in the same file.
- Squash-merge trap: `git merge-base --is-ancestor` over every remote branch
  against `origin/main` (109 of 115 unmerged) against the PR API (91 of the last
  100 merged).
- PR clustering: PR API `created_at` / `merged_at` over PRs #187 to #204.

Still open, and none of it goes into a draft first:

- [ ] Actual field names in omp session jsonl. `cat` a file.
- [ ] Does parent cumulative usage include subagent spend? Spawn two, compare.
- [ ] Does `/compact` rewrite or append? This caps backfill depth.
- [ ] Does omp preserve pi's `PI_SESSION_ID` env vars in the bash tool? If yes,
      the extension may be unnecessary.
- [ ] Does omp duplicate persisted messages the way Claude Code does, or is its
      usage cumulative as the notes assume? The two harnesses need opposite
      handling and the answer decides the reader's core loop.
- [ ] Cache read and write pricing must be priced separately. **Partly answered:**
      cache writes are 74.2% of the measured session bill and a single write
      multiplier understates by 27.8%, so the TTL split is required, not
      optional. Confirm omp reports the TTL split at all; if it does not, that is
      a hard ceiling on accuracy for omp and the reason to keep the Claude Code
      reader honest.
- [ ] Anthropic rates and cache multipliers came from the bundled `claude-api`
      skill reference on 2026-09-05. Recheck against the published pricing page
      before any dollar figure is drafted, and record the date read.
- [ ] Whether Claude Code cloud sessions expose a `cost_usd` that agrees with
      the locally priced total. That is the `cost_src` question and the smallest
      version of the reconciliation test.
