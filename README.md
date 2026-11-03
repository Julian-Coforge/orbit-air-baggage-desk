# Orbit Air Baggage Desk

A command line claims desk for Orbit Air's lost, delayed, and damaged baggage claims.
It files claims, assigns them to agents, tracks every status change, and escalates
claims that run past their response deadline. Built with Python 3.14 and SQLite.

## Install

```bash
git clone https://github.com/Julian-Coforge/orbit-air-baggage-desk.git
cd orbit-air-baggage-desk
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Test and lint

```bash
pytest
ruff check .
```

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

**What I changed.** Nothing in the code or tests: no defect was found. Checks 4 and 5
were run as one-off scripts, not committed tests. Filing atomicity is covered by a
committed test on the escalation branch (the rollback test), and the UTC handling of
`--now` by the CLI tests.
