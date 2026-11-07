import { draftReply, money } from '../meta'
import type { PendingPayment, Ticket } from '../types'

export default function Approvals({
  ticket,
  approver,
  onApprover,
  busy,
  onPay,
  onClose,
}: {
  ticket: Ticket
  approver: string
  onApprover: (v: string) => void
  busy: boolean
  onPay: (p: PendingPayment) => void
  onClose: () => void
}) {
  const reply = draftReply(ticket.notes)
  const named = approver.trim().length > 0
  return (
    <section className="card approvals" aria-labelledby="approve-h">
      <div className="section-head">
        <h2 id="approve-h">Needs your approval</h2>
        <span className="chip needs_you">Ticket #{ticket.id}</span>
      </div>
      <p className="muted small">The pups only prepared this. Nothing is paid or closed until you click.</p>

      <label className="field-label" htmlFor="approver">Approving as</label>
      <input id="approver" className="text-input" value={approver} onChange={(e) => onApprover(e.target.value)} placeholder="Your name" maxLength={80} />

      {ticket.pending_payments.map((p) => (
        <div className="approval" key={`${p.kind}-${p.ref_id}`}>
          <div>
            <p className="approval-title">{p.kind === 'rent' ? 'Pay the rent' : 'Approve the purchase'}</p>
            <p className="approval-detail">
              <b>{money(p.amount)}</b> to {p.payee}
              <br />
              <span className="muted">{p.description} · due {p.due_date}</span>
            </p>
          </div>
          <button type="button" className="btn primary" disabled={busy || !named} onClick={() => onPay(p)}>
            Approve and pay
          </button>
        </div>
      ))}

      {reply && (
        <div className="approval column">
          <p className="approval-title">Review the drafted reply <span className="muted small">(not sent)</span></p>
          <blockquote className="draft">{reply.replace(/^DRAFT REPLY to [^:]+:\s*/i, '')}</blockquote>
        </div>
      )}

      <div className="approval">
        <div>
          <p className="approval-title">Close the ticket</p>
          <p className="approval-detail muted">
            {ticket.pending_payments.length > 0
              ? 'Available after the payment above is approved.'
              : reply
                ? 'You have read the draft and the agents’ work.'
                : 'You have read the agents’ work.'}
          </p>
        </div>
        <button type="button" className="btn" disabled={busy || !named || !ticket.can_close} onClick={onClose}>
          Approve and resolve
        </button>
      </div>
    </section>
  )
}
