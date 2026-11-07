"""Run the Campus Customs agent team.

  python backend/run.py                                  work every open ticket
  python backend/run.py --message "Handle ticket 102"    something specific
  python backend/run.py --approver "Katie Bays"          let payments go through, approved by this person
  python backend/run.py --db path/to/copy.db             work on a copy of the database

Without --approver the agents can look, plan and update tickets, but no money moves.
Every agent step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from audit import AUDIT_PATH
from boss import run_team
from models import RunRequest

DEFAULT_MESSAGE = (
    "Work all the open tickets. Triage the queue, get each one handled by the right departments, "
    "update the tickets, and tell me what needs my approval."
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--message", default=DEFAULT_MESSAGE)
    p.add_argument("--approver", default=None, help="A real person who approves payments for this run.")
    p.add_argument("--db", type=Path, default=None, help="Database file (default: data/campus_customs_new.db).")
    args = p.parse_args()
    req = RunRequest(message=args.message, approver=args.approver)

    result, run_id = asyncio.run(run_team(req.message, approver=req.approver, db_path=args.db))

    out = sys.stdout
    out.write(f"\nRun {run_id}\n\n{result.answer}\n\nTickets\n")
    for o in result.outcomes:
        out.write(f"- #{o.ticket_id} [{o.status}] {o.summary} (by {', '.join(o.handled_by) or 'boss'})\n")
    if result.needs_human:
        out.write("\nNeeds a person\n")
        for n in result.needs_human:
            out.write(f"- {n}\n")
    out.write(f"\nAudit trail: {AUDIT_PATH}\n")


if __name__ == "__main__":
    main()
