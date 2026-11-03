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
