"""Campus Customs MCP server (FastMCP).

Tools over data/campus_customs_new.db (R = read only, W = writes):
  check_order(ticket_id)                       R  stock + price for an order ticket
  suggest_restock(low_stock, restock_to)       R  what to reorder, from which vendor
  pay_invoice(invoice_id, approved_by)         W  pay an open vendor invoice
  list_tickets(status)                         R  the ticket queue
  get_ticket(ticket_id)                        R  one ticket with its linked lease, invoice and stock
  update_ticket(ticket_id, status, note, by)   W  move a ticket along and log a note
  get_stock(sku, size)                         R  units on hand and list price
  quote_price(sku, qty, discount_pct)          R  price, cost and margin for a quantity and discount
  list_invoices(status)                        R  vendor bills, with overdue days
  get_cash_position()                          R  cash, bills and rent due, and what is left
  get_lease(lease_id)                          R  lease with days until rent is due
  pay_rent(lease_id, approved_by)              W  pay rent that is due soon

Run (stdio):  python server.py
Override the database with the CAMPUS_CUSTOMS_DB environment variable (used for tests).
"""

from __future__ import annotations

import calendar
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB") or HERE.parent / "data" / "campus_customs_new.db")

mcp = FastMCP("campus-customs")

# Which vendor specialty serves which kind of product (the sku's middle part, e.g. CC-MUG-CREST).
VENDOR_KEYWORD = {"HOOD": "apparel", "TEE": "apparel", "HAT": "apparel", "MUG": "mugs"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' lives in the desk table, not on the computer clock."""
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


@mcp.tool
def check_order(ticket_id: int) -> dict[str, Any]:
    """Check a customer order ticket against stock and price.

    Looks up the ticket's sku, size and quantity, then reports units on hand,
    whether the order can be filled, the list price, the order total and any
    shortfall. Read only.
    """
    with _connect() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "error": f"No ticket {ticket_id}."}
        if t["type"] != "customer_order":
            return {"ok": False, "error": f"Ticket {ticket_id} is a {t['type']}, not a customer_order."}
        if not (t["sku"] and t["size"] and t["qty"]):
            return {"ok": False, "error": f"Ticket {ticket_id} is missing a sku, size or quantity."}

        stock = conn.execute(
            "SELECT name, qty FROM inventory WHERE sku = ? AND size = ?", (t["sku"], t["size"])
        ).fetchone()
        if stock is None:
            return {"ok": False, "error": f"No inventory row for {t['sku']} size {t['size']}."}
        price = conn.execute("SELECT list_price FROM pricing WHERE sku = ?", (t["sku"],)).fetchone()
        list_price = price["list_price"] if price else None

        wanted, on_hand = t["qty"], stock["qty"]
        return {
            "ok": True,
            "ticket_id": ticket_id,
            "requester": t["requester"],
            "ticket_status": t["status"],
            "sku": t["sku"],
            "product": stock["name"],
            "size": t["size"],
            "qty_requested": wanted,
            "qty_in_stock": on_hand,
            "can_fill": on_hand >= wanted,
            "shortfall": max(wanted - on_hand, 0),
            "list_price": list_price,
            "order_total": round(list_price * wanted, 2) if list_price is not None else None,
        }


@mcp.tool
def suggest_restock(low_stock: int = 3, restock_to: int = 10) -> dict[str, Any]:
    """Suggest what to reorder: every sold-out or low-stock item with a vendor.

    An item is low when its quantity is `low_stock` or fewer. The suggestion tops
    it up to `restock_to` units, picks the vendor whose specialty fits, and
    estimates cost from unit_cost and arrival from the vendor's lead time.
    Read only: it proposes, a person decides whether to order.
    """
    with _connect() as conn:
        today = date.fromisoformat(_today(conn))
        vendors = conn.execute("SELECT * FROM vendors").fetchall()
        rows = conn.execute(
            "SELECT i.sku, i.name, i.size, i.qty, p.unit_cost "
            "FROM inventory i LEFT JOIN pricing p ON p.sku = i.sku "
            "WHERE i.qty <= ? ORDER BY i.qty, i.sku, i.size",
            (low_stock,),
        ).fetchall()

        items = []
        for r in rows:
            kind = next((k for k in VENDOR_KEYWORD if f"-{k}-" in r["sku"]), None)
            vendor = next(
                (v for v in vendors if kind and VENDOR_KEYWORD[kind] in v["specialty"].lower()), None
            )
            order_qty = max(restock_to - r["qty"], 0)
            items.append(
                {
                    "sku": r["sku"],
                    "product": r["name"],
                    "size": r["size"],
                    "qty_in_stock": r["qty"],
                    "status": "sold out" if r["qty"] == 0 else "low",
                    "suggested_order_qty": order_qty,
                    "estimated_cost": round(order_qty * r["unit_cost"], 2) if r["unit_cost"] is not None else None,
                    "vendor": vendor["name"] if vendor else None,
                    "lead_days": vendor["lead_days"] if vendor else None,
                    "expected_arrival": (today + timedelta(days=vendor["lead_days"])).isoformat() if vendor else None,
                }
            )
        return {
            "ok": True,
            "as_of": today.isoformat(),
            "low_stock_threshold": low_stock,
            "restock_to": restock_to,
            "items": items,
            "total_estimated_cost": round(sum(i["estimated_cost"] or 0 for i in items), 2),
        }


@mcp.tool
def pay_invoice(invoice_id: int, approved_by: str) -> dict[str, Any]:
    """Pay an open vendor invoice from the checking account.

    Refuses unless the invoice exists and is still open, a person is named in
    `approved_by`, and the checking balance covers the amount. When every check
    passes it records a payment, marks the invoice paid and lowers the balance.
    This is the only tool that changes the database.
    """
    approver = (approved_by or "").strip()
    if not approver:
        return {"ok": False, "paid": False, "error": "Refused: name the person who approves this payment (approved_by)."}

    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")  # lock so two payments cannot both spend the same cash
        today = _today(conn)
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if inv is None:
            return {"ok": False, "paid": False, "error": f"Refused: no invoice {invoice_id}."}
        if inv["status"] != "open":
            return {"ok": False, "paid": False, "error": f"Refused: invoice {invoice_id} is {inv['status']}, not open."}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if acct is None:
            return {"ok": False, "paid": False, "error": "Refused: there is no checking account."}
        if acct["balance"] < inv["amount"]:
            return {
                "ok": False,
                "paid": False,
                "error": f"Refused: checking has ${acct['balance']:.2f}, invoice {invoice_id} is ${inv['amount']:.2f}.",
            }

        new_balance = round(acct["balance"] - inv["amount"], 2)
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES ('invoice', ?, ?, 'checking', ?, ?)",
            (invoice_id, inv["amount"], today, approver),
        )
        conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today))
        conn.commit()
        return {
            "ok": True,
            "paid": True,
            "payment_id": cur.lastrowid,
            "invoice_id": invoice_id,
            "amount": inv["amount"],
            "was_overdue": inv["due_date"] < today,
            "approved_by": approver,
            "paid_at": today,
            "checking_balance_after": new_balance,
        }


TICKET_STATUSES = ("open", "in_progress", "waiting_on_approval", "resolved")
RENT_PAY_WINDOW_DAYS = 7  # rent can only be paid this close to its due date


def _add_month(d: date) -> date:
    year, month = d.year + d.month // 12, d.month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _lease_view(row: sqlite3.Row, today: date) -> dict[str, Any]:
    due = date.fromisoformat(row["next_due"])
    return {
        "lease_id": row["id"],
        "space_name": row["space_name"],
        "landlord": row["landlord"],
        "monthly_rent": row["monthly_rent"],
        "next_due": row["next_due"],
        "days_until_due": (due - today).days,
        "notes": row["notes"],
    }


def _invoice_view(row: sqlite3.Row, today: date) -> dict[str, Any]:
    days_late = (today - date.fromisoformat(row["due_date"])).days
    return {
        "invoice_id": row["id"],
        "vendor": row["vendor_name"],
        "amount": row["amount"],
        "due_date": row["due_date"],
        "status": row["status"],
        "description": row["description"],
        "overdue": row["status"] == "open" and days_late > 0,
        "days_overdue": max(days_late, 0) if row["status"] == "open" else 0,
    }


@mcp.tool
def list_tickets(status: str = "open") -> dict[str, Any]:
    """List tickets in the queue, oldest first. `status` is open, in_progress,
    waiting_on_approval, resolved, or all. Read only."""
    with _connect() as conn:
        today = _today(conn)
        if status == "all":
            rows = conn.execute("SELECT * FROM tickets ORDER BY created_at").fetchall()
        else:
            rows = conn.execute("SELECT * FROM tickets WHERE status = ? ORDER BY created_at", (status,)).fetchall()
        return {"ok": True, "today": today, "count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Get one ticket with everything it links to: its lease, its invoice, and
    stock and price for its product. Read only."""
    with _connect() as conn:
        today = date.fromisoformat(_today(conn))
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "error": f"No ticket {ticket_id}."}
        linked: dict[str, Any] = {}
        if t["lease_id"]:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            linked["lease"] = _lease_view(lease, today) if lease else None
        if t["invoice_id"]:
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (t["invoice_id"],),
            ).fetchone()
            linked["invoice"] = _invoice_view(inv, today) if inv else None
        if t["sku"]:
            stock = conn.execute(
                "SELECT i.name, i.size, i.qty, i.location, p.list_price, p.unit_cost "
                "FROM inventory i LEFT JOIN pricing p ON p.sku = i.sku WHERE i.sku = ? AND (? IS NULL OR i.size = ?)",
                (t["sku"], t["size"], t["size"]),
            ).fetchall()
            linked["stock"] = [dict(r) for r in stock]
        return {"ok": True, "today": today.isoformat(), "ticket": dict(t), "linked": linked}


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str, updated_by: str) -> dict[str, Any]:
    """Set a ticket's status and append a dated note saying who wrote it.
    status: open, in_progress, waiting_on_approval or resolved. Changes the database."""
    if status not in TICKET_STATUSES:
        return {"ok": False, "error": f"Refused: status must be one of {', '.join(TICKET_STATUSES)}."}
    note, who = (note or "").strip()[:1000], (updated_by or "").strip()
    if not note or not who:
        return {"ok": False, "error": "Refused: give a note and say who is updating (updated_by)."}
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        today = _today(conn)
        t = conn.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "error": f"No ticket {ticket_id}."}
        notes = ((t["notes"] + "\n") if t["notes"] else "") + f"[{today} {who}] {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
        conn.commit()
        return {"ok": True, "ticket_id": ticket_id, "old_status": t["status"], "new_status": status}


@mcp.tool
def get_stock(sku: str, size: str | None = None) -> dict[str, Any]:
    """Units on hand, location and list price for a sku, for one size or every size. Read only."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT i.sku, i.name, i.size, i.qty, i.location, p.list_price FROM inventory i "
            "LEFT JOIN pricing p ON p.sku = i.sku WHERE i.sku = ? AND (? IS NULL OR i.size = ?) ORDER BY i.size",
            (sku, size, size),
        ).fetchall()
        if not rows:
            return {"ok": False, "error": f"No inventory for {sku}" + (f" size {size}." if size else ".")}
        return {"ok": True, "items": [dict(r) for r in rows], "total_qty": sum(r["qty"] for r in rows)}


@mcp.tool
def quote_price(sku: str, qty: int, discount_pct: float = 0.0) -> dict[str, Any]:
    """Price a quantity at a discount: unit price, total, and margin over unit cost.
    Shows the biggest discount that would still not lose money. It only prices;
    it does not approve a discount. Read only."""
    if qty <= 0 or not 0 <= discount_pct <= 100:
        return {"ok": False, "error": "Refused: qty must be above 0 and discount_pct between 0 and 100."}
    with _connect() as conn:
        p = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if p is None:
            return {"ok": False, "error": f"No price for {sku}."}
        unit = round(p["list_price"] * (1 - discount_pct / 100), 2)
        return {
            "ok": True,
            "sku": sku,
            "qty": qty,
            "list_price": p["list_price"],
            "unit_cost": p["unit_cost"],
            "discount_pct": discount_pct,
            "discounted_unit_price": unit,
            "total": round(unit * qty, 2),
            "margin_per_unit": round(unit - p["unit_cost"], 2),
            "margin_pct": round((unit - p["unit_cost"]) / unit * 100, 1) if unit else None,
            "total_margin": round((unit - p["unit_cost"]) * qty, 2),
            "loses_money": unit < p["unit_cost"],
            "max_discount_pct_before_loss": round((p["list_price"] - p["unit_cost"]) / p["list_price"] * 100, 1),
        }


@mcp.tool
def list_invoices(status: str = "open") -> dict[str, Any]:
    """List vendor invoices (status open, paid, or all) with the vendor name and
    how many days overdue each open one is. Read only."""
    with _connect() as conn:
        today = date.fromisoformat(_today(conn))
        sql = "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id"
        rows = conn.execute(sql + ("" if status == "all" else " WHERE i.status = ?") + " ORDER BY i.due_date",
                            () if status == "all" else (status,)).fetchall()
        return {"ok": True, "today": today.isoformat(), "invoices": [_invoice_view(r, today) for r in rows]}


@mcp.tool
def get_cash_position() -> dict[str, Any]:
    """Checking balance, open bills, rent due in the next 7 days, and the cash left
    if all of them were paid. Read only."""
    with _connect() as conn:
        today = date.fromisoformat(_today(conn))
        acct = conn.execute("SELECT balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
        inv = [_invoice_view(r, today) for r in conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open'"
        ).fetchall()]
        rent = [_lease_view(r, today) for r in conn.execute("SELECT * FROM leases").fetchall()]
        rent_soon = [r for r in rent if r["days_until_due"] <= RENT_PAY_WINDOW_DAYS]
        bills, rents = sum(i["amount"] for i in inv), sum(r["monthly_rent"] for r in rent_soon)
        return {
            "ok": True,
            "today": today.isoformat(),
            "checking_balance": acct["balance"],
            "balance_as_of": acct["date"],
            "open_invoices_total": round(bills, 2),
            "overdue_invoices_total": round(sum(i["amount"] for i in inv if i["overdue"]), 2),
            "rent_due_within_7_days": round(rents, 2),
            "cash_after_paying_everything": round(acct["balance"] - bills - rents, 2),
        }


@mcp.tool
def get_lease(lease_id: int) -> dict[str, Any]:
    """Get a lease with its rent, due date and days until it is due. Read only."""
    with _connect() as conn:
        today = date.fromisoformat(_today(conn))
        row = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": f"No lease {lease_id}."}
        return {"ok": True, "today": today.isoformat(), "lease": _lease_view(row, today)}


@mcp.tool
def pay_rent(lease_id: int, approved_by: str) -> dict[str, Any]:
    """Pay a lease's monthly rent from checking. Refuses unless a person approves,
    rent is due within 7 days, and cash covers it. Records the payment and moves
    next_due forward one month. Changes the database."""
    approver = (approved_by or "").strip()
    if not approver:
        return {"ok": False, "paid": False, "error": "Refused: name the person who approves this payment (approved_by)."}
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        today = date.fromisoformat(_today(conn))
        row = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if row is None:
            return {"ok": False, "paid": False, "error": f"Refused: no lease {lease_id}."}
        due = date.fromisoformat(row["next_due"])
        if (due - today).days > RENT_PAY_WINDOW_DAYS:
            return {"ok": False, "paid": False,
                    "error": f"Refused: rent is not due until {row['next_due']}, more than {RENT_PAY_WINDOW_DAYS} days away."}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if acct is None or acct["balance"] < row["monthly_rent"]:
            have = acct["balance"] if acct else 0
            return {"ok": False, "paid": False,
                    "error": f"Refused: checking has ${have:.2f}, rent is ${row['monthly_rent']:.2f}."}
        new_balance = round(acct["balance"] - row["monthly_rent"], 2)
        new_due = _add_month(due).isoformat()
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES ('rent', ?, ?, 'checking', ?, ?)",
            (lease_id, row["monthly_rent"], today.isoformat(), approver),
        )
        conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, lease_id))
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today.isoformat()))
        conn.commit()
        return {"ok": True, "paid": True, "payment_id": cur.lastrowid, "lease_id": lease_id,
                "amount": row["monthly_rent"], "approved_by": approver, "paid_at": today.isoformat(),
                "next_due": new_due, "checking_balance_after": new_balance}


if __name__ == "__main__":
    mcp.run()
