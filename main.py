"""Command line interface for the Orbit Air baggage claims desk.

Usage: python main.py [--now ISO_TIMESTAMP] [--db PATH] <command> ...

This file only reads the command line, picks the clock, calls one function in
claims.py and prints the result. All claim rules live in claims.py.
"""

import argparse
import csv
import sqlite3
import sys
from datetime import UTC, datetime

import claims
import db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py", description="Orbit Air baggage claims desk."
    )
    parser.add_argument(
        "--now",
        help="ISO timestamp to use instead of the real clock, e.g. 2026-11-02T14:00:00 "
        "(no offset means UTC)",
    )
    parser.add_argument(
        "--db", default=db.DEFAULT_DB_PATH, help=f"database file (default {db.DEFAULT_DB_PATH})"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    file_cmd = commands.add_parser("file", help="file a new claim")
    file_cmd.add_argument("--passenger", required=True)
    file_cmd.add_argument("--flight", required=True)
    file_cmd.add_argument("--type", required=True, help="delayed, lost or damaged")
    file_cmd.add_argument("--tier", required=True, help="standard, silver or gold")
    file_cmd.add_argument("--note", default="")
    file_cmd.add_argument("--by", default="desk", help="who is filing (default desk)")

    list_cmd = commands.add_parser("list", help="list claims")
    list_cmd.add_argument("--status")
    list_cmd.add_argument("--tier")

    assign_cmd = commands.add_parser("assign", help="assign an open or escalated claim")
    assign_cmd.add_argument("claim_id", type=int)
    assign_cmd.add_argument("--agent", required=True)
    assign_cmd.add_argument("--by", default="desk")

    for name, text in (
        ("resolve", "resolve an assigned or escalated claim"),
        ("close", "close a resolved claim"),
    ):
        cmd = commands.add_parser(name, help=text)
        cmd.add_argument("claim_id", type=int)
        cmd.add_argument("--by", default="desk")

    escalate_cmd = commands.add_parser("escalate", help="escalate every overdue claim")
    escalate_cmd.add_argument("--by", default="system")

    history_cmd = commands.add_parser("history", help="show one claim's history")
    history_cmd.add_argument("claim_id", type=int)

    seed_cmd = commands.add_parser("seed", help="load claims from a CSV file")
    seed_cmd.add_argument("csv_path")

    commands.add_parser("report", help="open and overdue counts by tier")
    return parser


def pick_clock(now_text: str | None) -> datetime:
    """The --now time if given, otherwise the real clock. The only clock read in the app."""
    if now_text is None:
        return datetime.now(UTC)
    try:
        return claims.to_utc(datetime.fromisoformat(now_text))
    except ValueError:
        raise claims.ClaimError(
            f"--now must be an ISO timestamp, e.g. 2026-11-02T14:00:00 (got {now_text!r})"
        ) from None


def print_claims(rows) -> None:
    if not rows:
        print("No claims found.")
        return
    print(f"{'ID':>3}  {'STATUS':<9}  {'TIER':<8}  {'TYPE':<7}  {'FLIGHT':<6}  "
          f"{'PASSENGER':<16}  {'AGENT':<8}  DEADLINE (UTC)")
    for row in rows:
        print(
            f"{row['id']:>3}  {row['status']:<9}  {row['tier']:<8}  {row['type']:<7}  "
            f"{row['flight']:<6}  {row['passenger']:<16}  {row['agent'] or '-':<8}  "
            f"{row['deadline']}"
        )


def read_seed_rows(path: str) -> list[dict[str, str]]:
    try:
        # utf-8-sig also reads files that start with a byte order mark (Excel "CSV UTF-8").
        with open(path, newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise claims.ClaimError(f"cannot read seed file {path}: {error.strerror}") from None
    except UnicodeDecodeError:
        raise claims.ClaimError(f"cannot read seed file {path}: it is not UTF-8 text") from None
    except csv.Error as error:
        raise claims.ClaimError(f"cannot read seed file {path}: {error}") from None


def run(args: argparse.Namespace, conn, now: datetime) -> None:
    match args.command:
        case "file":
            claim_id = claims.file_claim(
                conn, args.passenger, args.flight, args.type, args.tier, args.note,
                now=now, changed_by=args.by,
            )
            claim = claims.get_claim(conn, claim_id)
            print(f"Filed claim {claim_id} ({claim['tier']}): deadline {claim['deadline']} UTC")
        case "list":
            print_claims(claims.list_claims(conn, status=args.status, tier=args.tier))
        case "assign":
            claims.assign_claim(conn, args.claim_id, args.agent, now=now, changed_by=args.by)
            print(f"Claim {args.claim_id} assigned to {args.agent.strip()}.")
        case "resolve":
            claims.resolve_claim(conn, args.claim_id, now=now, changed_by=args.by)
            print(f"Claim {args.claim_id} resolved.")
        case "close":
            claims.close_claim(conn, args.claim_id, now=now, changed_by=args.by)
            print(f"Claim {args.claim_id} closed.")
        case "escalate":
            escalated = claims.escalate_overdue(conn, now=now, changed_by=args.by)
            if escalated:
                ids = ", ".join(str(claim_id) for claim_id in escalated)
                print(f"Escalated {len(escalated)} claim(s): {ids}")
            else:
                print(f"No claims are overdue at {claims.format_time(now)} UTC.")
        case "history":
            for entry in claims.get_history(conn, args.claim_id):
                old = entry["old_status"] or "(filed)"
                print(
                    f"{entry['changed_at']}  {old} -> {entry['new_status']}  "
                    f"by {entry['changed_by']}"
                )
        case "seed":
            ids = claims.seed_claims(conn, read_seed_rows(args.csv_path), now=now)
            print(f"Loaded {len(ids)} claims from {args.csv_path} (ids {ids[0]}-{ids[-1]})."
                  if ids else f"Loaded 0 claims from {args.csv_path}.")
        case "report":
            print(f"Claims at {claims.format_time(now)} UTC")
            print(f"{'TIER':<9} {'OPEN':>5} {'OVERDUE':>8}")
            for tier, counts in claims.report_counts(conn, now=now).items():
                print(f"{tier:<9} {counts['open']:>5} {counts['overdue']:>8}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        now = pick_clock(args.now)
        conn = db.connect(args.db)
        try:
            run(args, conn, now)
        finally:
            conn.close()
    except claims.ClaimError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except sqlite3.Error as error:
        print(f"Error: database problem with {args.db}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
