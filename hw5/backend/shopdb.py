"""Plain database helpers for the dashboard routes: read tickets and cash, and reset to the original.

Reads open the database read-only. Everything that changes data goes through the MCP server
(see mcp_client.py), except reset, which restores the whole file from the original.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from config import DEFAULT_DB, ORIGINAL_DB


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_tickets(db: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    conn = _ro(db)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id")]
    finally:
        conn.close()


def get_ticket(ticket_id: int, db: Path = DEFAULT_DB) -> dict[str, Any] | None:
    conn = _ro(db)
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def checking_balance(db: Path = DEFAULT_DB) -> dict[str, Any]:
    conn = _ro(db)
    try:
        row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
        return {"account": row["name"], "balance": row["balance"], "as_of": row["date"]}
    finally:
        conn.close()


def reset_db(db: Path = DEFAULT_DB, original: Path = ORIGINAL_DB) -> None:
    """Put every table back to the original values by copying the original database over the working one.

    Uses SQLite's backup, which is safe even if another process has the file open.
    """
    src = _ro(original)
    dst = sqlite3.connect(db)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


RENT_WINDOW_DAYS = 7  # same window the MCP server uses before it will pay rent


def pending_payments(ticket: dict[str, Any], db: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    """Unpaid money linked to a ticket: its open vendor invoice, and its lease if rent is due soon."""
    from datetime import date

    conn = _ro(db)
    try:
        today = date.fromisoformat(conn.execute("SELECT date_today FROM desk").fetchone()["date_today"])
        out: list[dict[str, Any]] = []
        if ticket.get("invoice_id"):
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ticket["invoice_id"],),
            ).fetchone()
            if inv and inv["status"] == "open":
                out.append(
                    {
                        "kind": "invoice",
                        "ref_id": inv["id"],
                        "amount": inv["amount"],
                        "payee": inv["vendor"],
                        "due_date": inv["due_date"],
                        "description": inv["description"] or f"Invoice {inv['id']}",
                    }
                )
        if ticket.get("lease_id"):
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            if lease and (date.fromisoformat(lease["next_due"]) - today).days <= RENT_WINDOW_DAYS:
                out.append(
                    {
                        "kind": "rent",
                        "ref_id": lease["id"],
                        "amount": lease["monthly_rent"],
                        "payee": lease["landlord"],
                        "due_date": lease["next_due"],
                        "description": f"Rent for {lease['space_name']}",
                    }
                )
        return out
    finally:
        conn.close()


def list_payments(db: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    """Every payment in order, with the payee (vendor or landlord) and the ticket it belongs to."""
    conn = _ro(db)
    try:
        out = []
        for r in conn.execute("SELECT * FROM payments ORDER BY id"):
            row = dict(r)
            payee = desc = ticket = None
            if r["kind"] == "invoice" and r["ref_id"] is not None:
                inv = conn.execute(
                    "SELECT i.description, v.name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                    (r["ref_id"],),
                ).fetchone()
                if inv:
                    payee, desc = inv["name"], inv["description"]
                t = conn.execute("SELECT id FROM tickets WHERE invoice_id = ? ORDER BY id LIMIT 1", (r["ref_id"],)).fetchone()
                ticket = t["id"] if t else None
            elif r["kind"] == "rent" and r["ref_id"] is not None:
                lease = conn.execute("SELECT landlord, space_name FROM leases WHERE id = ?", (r["ref_id"],)).fetchone()
                if lease:
                    payee, desc = lease["landlord"], f"Rent for {lease['space_name']}"
                t = conn.execute("SELECT id FROM tickets WHERE lease_id = ? ORDER BY id LIMIT 1", (r["ref_id"],)).fetchone()
                ticket = t["id"] if t else None
            out.append({**row, "payee": payee, "description": desc, "ticket_id": ticket})
        return out
    finally:
        conn.close()
