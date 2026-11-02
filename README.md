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

## Setup Check

_To be filled in after testing the deny rule in a fresh Claude Code session._
