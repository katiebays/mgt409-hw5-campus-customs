import { PHASE_LABEL, TICKET_TYPE, money, phaseOf } from '../meta'
import type { Ticket } from '../types'

const ICON: Record<string, string> = { customer_order: '👕', rent_notice: '🏛️', price_override: '🏷️' }

function ask(t: Ticket): string {
  if (t.type === 'customer_order') return `${t.qty ?? 1} × ${t.sku} · size ${t.size}`
  if (t.type === 'price_override') return `${t.qty} × ${t.sku} · size ${t.size}`
  const rent = t.pending_payments.find((p) => p.kind === 'rent')
  return rent ? `${money(rent.amount)} due ${rent.due_date}` : (t.notes ?? '').split('\n')[0]
}

export default function Tickets({
  tickets,
  selectedId,
  workingId,
  onSelect,
  onRun,
}: {
  tickets: Ticket[]
  selectedId: number | null
  workingId: number | null
  onSelect: (id: number) => void
  onRun: (id: number) => void
}) {
  return (
    <section aria-labelledby="tickets-h">
      <div className="section-head">
        <h2 id="tickets-h">Tickets</h2>
        <span className="muted small">
          {tickets.filter((t) => t.state === 'resolved').length} of {tickets.length} resolved
        </span>
      </div>
      <ul className="tickets">
        {tickets.map((t) => {
          const working = workingId === t.id
          const phase = phaseOf(t, working)
          const selected = selectedId === t.id
          return (
            <li key={t.id} className={`ticket ${phase} ${selected ? 'selected' : ''}`}>
              <button type="button" className="ticket-main" onClick={() => onSelect(t.id)} aria-pressed={selected}>
                <span className="ticket-id">#{t.id}</span>
                <span className="ticket-body">
                  <span className="ticket-subject">
                    <span aria-hidden="true">{ICON[t.type] ?? '🎫'}</span> {t.subject}
                  </span>
                  <span className="ticket-meta">{TICKET_TYPE[t.type] ?? t.type} · {t.requester}</span>
                  <span className="ticket-ask">{ask(t)}</span>
                </span>
                <span className={`chip ${phase}`}>
                  {phase === 'resolved' && '✓ '}
                  {PHASE_LABEL[phase]}
                </span>
              </button>
              {selected && phase === 'open' && (
                <button type="button" className="throw" onClick={() => onRun(t.id)} disabled={workingId !== null}>
                  <span aria-hidden="true">🎾</span> Throw it to Handsome Dan
                </button>
              )}
              {phase === 'resolved' && <span className="stamp" aria-hidden="true">RESOLVED</span>}
            </li>
          )
        })}
        {tickets.length === 0 && <li className="muted">Loading tickets…</li>}
      </ul>
    </section>
  )
}
