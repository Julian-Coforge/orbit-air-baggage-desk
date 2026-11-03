# Orbit Air Baggage Desk

A command line claims desk for Orbit Air's lost, delayed, and damaged baggage claims.
It files claims, assigns them to agents, tracks every status change, and escalates
claims that run past their response deadline. Built with Python 3.12 and SQLite.

## Install

```bash
git clone https://github.com/Julian-Coforge/orbit-air-baggage-desk.git
cd orbit-air-baggage-desk
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Test and lint

```bash
pytest
ruff check .
```

## Run

Every command takes two global options before the command name:

- `--now ISO_TIMESTAMP` sets the current time (UTC if no offset is given). Without it the app reads the real clock. `main.py` is the only file that reads the clock.
- `--db PATH` picks the SQLite file (default `orbit_air.db`, which is git-ignored).

`file`, `assign`, `resolve`, `close` and `escalate` also take `--by NAME`, recorded in the history (default `desk`, or `system` for `escalate`). `seed` always records `seed`.

```bash
python main.py --help
python main.py [--now ISO_TIMESTAMP] [--db PATH] <command> ...
```

| Command | What it does |
| --- | --- |
| `file --passenger P --flight F --type lost\|delayed\|damaged --tier gold\|silver\|standard [--note N]` | Files a claim and sets its deadline (gold 4h, silver 24h, standard 72h) |
| `list [--status S] [--tier T]` | Lists claims in id order (notes are not printed) |
| `assign ID --agent NAME` | Assigns an open or escalated claim |
| `resolve ID` | Resolves an assigned or escalated claim |
| `close ID` | Closes a resolved claim |
| `escalate` | Escalates every open or assigned claim whose deadline has passed |
| `history ID` | Prints every status change for a claim, oldest first |
| `seed CSV_PATH` | Loads claims from a CSV; rejects the whole file if any row is invalid |
| `report` | Open and overdue counts per tier (STRETCH GOAL 2) |

### Command walkthrough

Real output from a fresh database (`walk.db`), run on 2026-11-03:

```console
$ python main.py --db walk.db --now 2026-11-02T09:00:00 seed seed_claims.csv
Loaded 12 claims from seed_claims.csv (ids 1-12).

$ python main.py --db walk.db --now 2026-11-02T09:30:00 file --passenger "Ada Lee" --flight OA101 --type lost --tier gold --note "Blue suitcase"
Filed claim 13 (gold): deadline 2026-11-02T13:30:00 UTC

$ python main.py --db walk.db list --tier gold
 ID  STATUS     TIER      TYPE     FLIGHT  PASSENGER         AGENT     DEADLINE (UTC)
  1  open       gold      lost     OA101   Amelia Hart       -         2026-11-02T13:00:00
  5  open       gold      lost     OA404   Elena Rossi       -         2026-11-02T13:00:00
  7  open       gold      delayed  OA606   George Lee        -         2026-11-02T13:00:00
  9  open       gold      damaged  OA707   Ibrahim Haddad    -         2026-11-02T13:00:00
 13  open       gold      lost     OA101   Ada Lee           -         2026-11-02T13:30:00

$ python main.py --db walk.db --now 2026-11-02T10:00:00 assign 13 --agent Dana
Claim 13 assigned to Dana.

$ python main.py --db walk.db --now 2026-11-02T11:00:00 resolve 13
Claim 13 resolved.

$ python main.py --db walk.db --now 2026-11-02T11:05:00 close 13
Claim 13 closed.

$ python main.py --db walk.db history 13
2026-11-02T09:30:00  (filed) -> open  by desk
2026-11-02T10:00:00  open -> assigned  by desk
2026-11-02T11:00:00  assigned -> resolved  by desk
2026-11-02T11:05:00  resolved -> closed  by desk

$ python main.py --db walk.db --now 2026-11-02T14:00:00 escalate
Escalated 4 claim(s): 1, 5, 7, 9

$ python main.py --db walk.db --now 2026-11-02T14:00:00 report
Claims at 2026-11-02T14:00:00 UTC
TIER       OPEN  OVERDUE
gold          4        4
silver        4        0
standard      4        0
```

Errors print `Error: ...` to stderr and exit with status 1:

```console
$ python main.py --db walk.db --now 2026-11-02T14:05:00 assign 13 --agent Priya
Error: cannot change claim 13 from closed to assigned

$ python main.py --db walk.db --now yesterday list
Error: --now must be an ISO timestamp, e.g. 2026-11-02T14:00:00 (got 'yesterday')

$ python main.py --db walk.db --now 2026-11-02T14:05:00 file --passenger "Zoe" --flight OA1 --type stolen --tier gold
Error: unknown type 'stolen': must be one of delayed, lost, damaged
```

## Overdue Demonstration

A gold claim filed at 08:00 has a 12:00 deadline. At exactly 12:00 it is not overdue; at 12:01 it is.
Claim 3 shows an assigned claim keeps its agent when escalated. Real output from a fresh `demo.db`:

```console
$ python main.py --db demo.db --now 2026-11-02T08:00:00 file --passenger "Ada Lee" --flight OA101 --type lost --tier gold
Filed claim 1 (gold): deadline 2026-11-02T12:00:00 UTC

$ python main.py --db demo.db --now 2026-11-02T08:00:00 file --passenger "Ben Ortiz" --flight OA202 --type delayed --tier silver
Filed claim 2 (silver): deadline 2026-11-03T08:00:00 UTC

$ python main.py --db demo.db --now 2026-11-02T08:30:00 file --passenger "Cy Park" --flight OA303 --type damaged --tier gold
Filed claim 3 (gold): deadline 2026-11-02T12:30:00 UTC

$ python main.py --db demo.db --now 2026-11-02T09:00:00 assign 3 --agent Dana
Claim 3 assigned to Dana.

$ python main.py --db demo.db --now 2026-11-02T12:00:00 escalate
No claims are overdue at 2026-11-02T12:00:00 UTC.

$ python main.py --db demo.db --now 2026-11-02T12:01:00 escalate
Escalated 1 claim(s): 1

$ python main.py --db demo.db --now 2026-11-02T12:31:00 escalate
Escalated 1 claim(s): 3

$ python main.py --db demo.db list --status escalated
 ID  STATUS     TIER      TYPE     FLIGHT  PASSENGER         AGENT     DEADLINE (UTC)
  1  escalated  gold      lost     OA101   Ada Lee           -         2026-11-02T12:00:00
  3  escalated  gold      damaged  OA303   Cy Park           Dana      2026-11-02T12:30:00

$ python main.py --db demo.db --now 2026-11-02T12:31:00 report
Claims at 2026-11-02T12:31:00 UTC
TIER       OPEN  OVERDUE
gold          2        2
silver        1        0
standard      0        0

$ python main.py --db demo.db history 3
2026-11-02T08:30:00  (filed) -> open  by desk
2026-11-02T09:00:00  open -> assigned  by desk
2026-11-02T12:31:00  assigned -> escalated  by system
```

## Code Review

I ran `/code-review high main...feature/cli` on PR #4 before merging. It reported 10
findings. Fixes are in commit `9a9c114`; tests were not changed (still `47 passed`,
`ruff check .` clean).

| # | Finding | Action |
| --- | --- | --- |
| 1 | `seed` crashed with a `UnicodeDecodeError` traceback on a file that is not UTF-8 (reproduced) | Fixed: prints `Error: cannot read seed file ...: it is not UTF-8 text`, exit 1. `csv.Error` is handled the same way |
| 2 | A CSV with a byte order mark (Excel "CSV UTF-8") failed with `missing column(s) passenger` (reproduced) | Fixed: file is read as `utf-8-sig`. Re-run loaded the BOM file |
| 3 | `--db /nonexistent/x.db list` crashed with a `sqlite3.OperationalError` traceback (reproduced) | Fixed: prints `Error: database problem with /nonexistent/x.db: unable to open database file`, exit 1 |
| 4 | `seed` checked every row first but saved each row in its own transaction | Fixed: all rows now save in one transaction. Checked with a trigger that fails the 7th history insert: before the fix 6 claims stayed saved, after it 0 |
| 5 | CI docker job ran `seed` and `report` in two containers, so `report` read an empty database | Fixed: one container runs both |
| 6 | STRETCH GOAL 1 hook let an edit through if it could not read its input, and did not cover `NotebookEdit` | Fixed: unreadable input is blocked, `NotebookEdit` added to the matcher. It still does not see shell commands such as `sed -i`; the `tests/` checks in each PR catch those |
| 7 | `report_counts` repeated the tier list instead of using `TIER_HOURS` | Fixed |
| 8 | Seed rows with ` lost` or `Gold` (spaces or capitals) are rejected | No change: validation is strict on purpose and names the bad line, so the file can be corrected |
| 9 | README said every command takes `--by`, but `seed` does not | Fixed the README: `seed` always records `seed` |
| 10 | `file` re-reads the claim it just saved to print the deadline | No change: one extra read on a local database, kept for clarity |

## Linear Issues

Linear project: [Orbit Air Baggage Desk](https://linear.app/team2-week3-ert/project/orbit-air-baggage-desk-a3129c19e1dd)

| Branch | Issue |
|--------|-------|
| `feature/schema-and-filing` | [TEA-32: feature/schema-and-filing: tables, claim filing, validation and list](https://linear.app/team2-week3-ert/issue/TEA-32/featureschema-and-filing-tables-claim-filing-validation-and-list) |
| `feature/assign-and-status` | [TEA-33: feature/assign-and-status: assign, resolve, close and history](https://linear.app/team2-week3-ert/issue/TEA-33/featureassign-and-status-assign-resolve-close-and-history) |
| `feature/deadlines-and-escalation` | [TEA-34: feature/deadlines-and-escalation: overdue rule, escalation and rollback](https://linear.app/team2-week3-ert/issue/TEA-34/featuredeadlines-and-escalation-overdue-rule-escalation-and-rollback) |
| `feature/cli` | [TEA-35: feature/cli: all commands, --now option and seed](https://linear.app/team2-week3-ert/issue/TEA-35/featurecli-all-commands-now-option-and-seed) |

## Setup Check

_To be filled in after testing the deny rule in a fresh Claude Code session._

## Agent Log

### feature/schema-and-filing ([TEA-32](https://linear.app/team2-week3-ert/issue/TEA-32/featureschema-and-filing-tables-claim-filing-validation-and-list), PR #1)

**Prompt given.** "After these corrections, commit the updated PLAN.md before starting
feature implementation. Then proceed with the rubric-driven development workflow." The
agent was given the TEA-32 issue (problem, actual, expected, done when, constraint) and
PLAN.md section 8 as the spec.

**What the agent did.**
- Wrote the 11 tests in `tests/test_claims.py` plus `tests/conftest.py`, ran them, and
  committed them alone (`ee3bd5d`). They failed at collection:
  `ModuleNotFoundError: No module named 'db'`.
- Wrote `db.py` (tables and CHECK constraints) and `claims.py` (validation, tier
  deadlines, first history entry in one transaction, list filters), committed as
  `c6233a4`. Result: `11 passed`, `ruff check .` clean, CI green.
- Mistake caught on the way: the first test commit attempt failed `ruff check .` with
  `I001 Import block is un-sorted`, because ruff treated `db` and `claims` (which did not
  exist yet) as third-party. Fixed by declaring them first-party in `pyproject.toml`,
  not by changing the import order to suit the missing modules.

**What I checked.** I read `claims.py` and `db.py` against PLAN.md and the rubric, then
asked for these eight checks to be run against the branch code, without editing it:

1. Deadlines for a claim filed at `2026-11-02T10:00:00`: gold `2026-11-02T14:00:00`,
   silver `2026-11-03T10:00:00`, standard `2026-11-05T10:00:00`. All matched.
2. Filing writes exactly one history row: `old_status` NULL, `new_status` `open`, the
   right claim id, `changed_by` `Sam`, `changed_at` `2026-11-02T10:00:00`. Matched.
3. SQLite itself rejects a bad type, tier and status, a whitespace-only passenger and
   flight, and bad history statuses, each with `CHECK constraint failed`. All rejected.
4. With a temporary trigger forcing the first history insert to fail, `file_claim`
   raised `forced history failure` and left 0 claims and 0 history rows. After the
   trigger was dropped, filing worked again.
5. `now` of `12:00+02:00` and `05:00-05:00` both stored `filed_at`
   `2026-11-02T10:00:00`, with the right deadlines. A naive `10:00` was read as UTC. A
   gold claim filed at `23:30` got a deadline of `2026-11-03T03:30:00`.
6. Five claims came back in id order. `open`+`gold`, `assigned`+`gold` and an empty
   combination each returned the right ids. An unknown status filter raised a clear
   error.
7. `ee3bd5d` (tests) comes before `c6233a4` (code), and the code commit touches only
   `claims.py` and `db.py`. `git diff ee3bd5d -- tests/`,
   `git status --porcelain --untracked-files=all -- tests/` and
   `git log --oneline ee3bd5d..HEAD -- tests/` are all empty. Re-running `pytest` at
   `ee3bd5d` reproduced the `ModuleNotFoundError`.
8. The PR title starts with `feature/schema-and-filing`, links TEA-32, and shows the real
   failing and passing output.

**What I changed.** Nothing in the code or tests: no defect was found. Gap noted:
checks 4 (filing rollback) and 5 (timezone offsets) were run as one-off scripts, not
committed tests. The committed rollback test on `feature/deadlines-and-escalation`
covers the same transaction pattern for status changes.

### feature/assign-and-status ([TEA-33](https://linear.app/team2-week3-ert/issue/TEA-33/featureassign-and-status-assign-resolve-close-and-history), PR #2)

**Prompt given.** The workflow from PLAN.md section 7, with the TEA-33 issue (problem,
actual, expected, done when, constraint) and PLAN.md section 8's 12 planned tests as the
spec.

**What the agent did.**
- Wrote the 12 tests in `tests/test_status.py`, ran them, and committed them alone
  (`90cf4e1`). They failed at collection:
  `ImportError: cannot import name 'assign_claim' from 'claims'`.
- Added `ALLOWED_CHANGES`, a `_change_status` helper (look up the current status,
  reject any move not in the table, then update the claim and insert history inside
  one `with conn:`), `assign_claim`, `resolve_claim`, `close_claim` and `get_history`.
  Committed as `4741905`, which changes only `claims.py`. Result: `23 passed`,
  `ruff check .` clean, CI green.

**What I checked.** I reviewed the PR against PLAN.md, the status table in the brief
and the rubric. I noticed two places where the committed tests are thinner than the
behaviour they describe: only the open-to-closed rejection asserts the history count,
and the escalated reassignment test starts with no agent, so it never proves an
existing agent gets replaced. I had these checks run as a script against the branch
code, without changing it:

1. `ALLOWED_CHANGES` equals the brief's table exactly: 5 statuses, 7 allowed moves,
   `closed` maps to an empty set. Nothing missing, nothing extra.
2. `open` to `closed`, `open` to `resolved` and `closed` to `assigned` each raised
   `ClaimError` (`cannot change claim 1 from open to closed`, and so on). Status, agent
   and history count were identical before and after in all three cases, for example
   `('open', None, 1) -> ('open', None, 1)`.
3. A claim assigned to `Dana`, put into `escalated`, then reassigned to `Priya` ended
   as `('assigned', 'Priya')`. The last history row was `escalated` to `assigned`, by
   `Supervisor Kim`, at `2026-11-02T11:00:00`.
4. One assignment added exactly one history row (count 1 to 2) with the right
   `claim_id`, `open` to `assigned`, `Sam`, `2026-11-02T10:10:00`. The full life (file,
   assign, resolve, close) produced 4 rows in order, at 10:00, 10:10, 10:20 and 10:30.
5. In `_change_status` the claim `UPDATE` and the history insert are both inside the
   same `with conn:`, update first. With a temporary trigger forcing the history insert
   to fail, `assign_claim` raised `forced history failure` and the claim stayed
   `('open', None)` with 1 history row. The committed rollback test comes on the next
   branch.
6. `90cf4e1` (only `tests/test_status.py`, 12 tests collected) comes before `4741905`
   (only `claims.py`). `git diff 90cf4e1 -- tests/`,
   `git status --porcelain --untracked-files=all -- tests/` and
   `git log --oneline 90cf4e1..HEAD -- tests/` are all empty.
7. Locally on Python 3.14.6: `pytest -q` gave `23 passed`, `ruff check .` gave
   `All checks passed!`. GitHub Actions passed on `4741905`.

**What I changed.** Nothing: no defect was found. The two thin spots in the tests are
covered by checks 2 and 3 above rather than by editing committed tests.

### feature/deadlines-and-escalation ([TEA-34](https://linear.app/team2-week3-ert/issue/TEA-34/featuredeadlines-and-escalation-overdue-rule-escalation-and-rollback), PR #3)

**Prompt given.** The workflow from PLAN.md section 7, with the TEA-34 issue (problem,
actual, expected, done when, constraint) and PLAN.md section 8's 12 planned tests,
including the rollback test and the mutation check, as the spec.

**What the agent did.**
- Wrote the 12 tests in `tests/test_escalation.py` and committed them alone
  (`32e7562`). They failed at collection:
  `ImportError: cannot import name 'escalate_claim' from 'claims'`.
- Added `is_overdue` (`to_utc(now) > to_utc(deadline)`), `escalate_claim` (rejects a
  claim that is not overdue, then goes through `_change_status`) and `escalate_overdue`
  (open and assigned claims in id order, history by `system`, returns the ids).
  Committed as `f3b6d41`, which changes only `claims.py`. Result: `35 passed`, ruff
  clean, CI green.
- **Mistake caught.** PLAN.md's mutation-check command,
  `pytest tests/test_escalation.py -k rollback`, selected no test at all
  (`12 deselected`), because the test is named
  `test_failed_history_write_rolls_back_the_claim_change`. Run as written, the check
  would have "passed" without running anything. The agent noticed the `deselected`
  count, re-ran with `-k rolls_back`, and fixed PLAN.md in its own commit (`c515a78`).
- The rollback test calls `assign_claim`, whose transaction came from the previous
  branch. Its first failure was the file-level import error, not the rollback itself, so
  the mutation check below is the evidence that it catches a missing transaction.

**What I checked.** I reviewed the PR against PLAN.md and the rubric. GitHub Actions
passed, the commit order was right, and I asked for these checks to be run as a script
against the branch code, without changing it:

1. **Deadline boundary.** Gold claim filed `2026-11-02T10:00:00`, deadline
   `14:00:00`. `escalate_claim` at `13:59` and at exactly `14:00` both raised
   `claim 1 is not overdue: its deadline is 2026-11-02T14:00:00 UTC`, with the claim
   unchanged at `('open', None, 1)` (status, agent, history count). At `14:01` it
   succeeded: `('escalated', None, 2)`.
2. **Eligible statuses.** With one overdue claim in each status, `escalate_overdue` at
   16:00 returned `[1, 2]` (the open and the assigned claim). The resolved, closed and
   already escalated claims kept identical status, agent and history count:
   `('resolved', 'Dana', 3)`, `('closed', 'Dana', 4)`, `('escalated', None, 2)`.
3. **Agent kept.** A claim assigned to Dana and escalated at 14:01 became
   `('escalated', 'Dana', 3)`. Its last history row: `assigned` to `escalated`,
   `system`, `2026-11-02T14:01:00`.
4. **Bulk escalation.** Five claims (gold open overdue, silver open not overdue, gold
   assigned overdue, standard open filed four days earlier, gold resolved). It returned
   `[1, 3, 4]` in ascending order and added exactly 3 history rows. A second run
   returned `[]` and the history total stayed at 11.
5. **UTC.** For deadline `14:00Z`: `16:00+02:00` was not overdue, `16:01+02:00` was,
   `09:00-05:00` was not, and a naive `14:01` (read as UTC) was. `is_overdue` compares
   `to_utc(now) > to_utc(deadline)`. A search for `datetime.now`, `time.time`,
   `date.today` and `utcnow` in `claims.py` and `db.py` found nothing.
6. **Rollback and mutation.** With `with conn:` replaced by `if True:` in
   `_change_status`,
   `pytest -q tests/test_escalation.py -k rolls_back` gave
   `AssertionError: assert 'assigned' == 'open'` and `1 failed, 11 deselected`. With the
   file restored (`git diff --quiet HEAD -- claims.py` confirmed it was identical), it
   gave `1 passed, 11 deselected`. Run twice, by the agent and again for this review,
   with the same results.
7. **Transaction scope.** Each escalation is atomic. With a trigger failing only the
   second claim's escalation history row, that claim stayed `('open', None, 1)`, but the
   first claim stayed `('escalated', None, 2)` and `escalate_overdue` raised before
   returning. So a batch is not all-or-nothing: each claim is its own transaction. That
   matches the plan, and nothing in the brief asks for batch atomicity.
8. **Workflow.** `32e7562` changes only `tests/test_escalation.py` (12 tests),
   `f3b6d41` only `claims.py`, `c515a78` only `PLAN.md`. `git diff 32e7562 -- tests/`,
   `git status --porcelain --untracked-files=all -- tests/` and
   `git log --oneline 32e7562..HEAD -- tests/` are all empty. Locally: `pytest -q` gave
   `35 passed`, `ruff check .` gave `All checks passed!`.

**What I changed.** No code or test changes: no defect was found. The only correction
on this branch is the PLAN.md selector fix described above.
