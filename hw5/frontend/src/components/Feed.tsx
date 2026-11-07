import { AGENTS, clip, shortTime } from '../meta'
import type { AgentEvent, AgentName } from '../types'

function humanLine(e: AgentEvent): string {
  const t = e.tools[0]
  if (!t) return 'Acted on the ticket.'
  let args: Record<string, unknown> = {}
  let res: Record<string, unknown> = {}
  try { args = JSON.parse(t.args) } catch { /* args may be cut short */ }
  try { res = JSON.parse(t.result) } catch { /* result may be cut short */ }
  if (e.stop_reason === 'refused') return `Tried ${t.name}, and it was refused.`
  if (t.name === 'pay_invoice') return `Approved the purchase: paid invoice ${args.invoice_id}${res.amount ? ` ($${Number(res.amount).toFixed(2)})` : ''}.`
  if (t.name === 'pay_rent') return `Approved the rent: paid lease ${args.lease_id}${res.amount ? ` ($${Number(res.amount).toFixed(2)})` : ''}.`
  if (t.name === 'update_ticket') return 'Reviewed the work and closed the ticket.'
  return `Used ${t.name}.`
}

/** What happened, newest first: each agent's words, the tools it used, and your own approvals. */
export default function Feed({ events }: { events: AgentEvent[] }) {
  const rows = [...events].reverse()
  return (
    <section aria-labelledby="feed-h">
      <div className="section-head">
        <h2 id="feed-h">Play by play</h2>
        <span className="muted small">{events.length} steps</span>
      </div>
      {rows.length === 0 && <p className="muted">Nothing yet. Throw a ticket to Handsome Dan and watch this fill in.</p>}
      <ol className="feed">
        {rows.map((e) => {
          const human = e.agent === 'human'
          const m = human ? null : AGENTS[e.agent as AgentName]
          return (
            <li key={e.seq} className={`feed-item ${human ? 'human' : ''}`} style={{ ['--agent' as string]: m?.color ?? '#00356b' }}>
              <div className="feed-head">
                <span className="swatch" aria-hidden="true" />
                <b>{human ? `You (${e.approver ?? ''})` : (m?.label ?? e.agent)}</b>
                <span className="muted small">step {e.iteration} · {shortTime(e.timestamp)}</span>
              </div>
              {human ? (
                <p className="said">{humanLine(e)}</p>
              ) : (
                <>
                  {e.said && <p className="said">{clip(e.said, 360)}</p>}
                  {e.tools.length > 0 && (
                    <p className="tools">
                      {e.tools.map((t, i) => (
                        <code key={i} title={`${t.args}\n→ ${t.result}`}>{t.name}</code>
                      ))}
                    </p>
                  )}
                </>
              )}
              {e.guardrail_events.map((g) => (
                <p key={g} className="guard small">🛡 {g}</p>
              ))}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
