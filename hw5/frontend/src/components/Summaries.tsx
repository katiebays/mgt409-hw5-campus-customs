import { AGENTS, SPECIALIST_ORDER, firstSentences } from '../meta'
import type { AgentEvent, AgentName } from '../types'

type Status = 'unused' | 'working' | 'done'

interface Summary {
  agent: AgentName
  status: Status
  steps: number
  tools: string[]
  said: string | null
  asked: AgentName[]
  guard: string[]
}

export function summarize(events: AgentEvent[]): Record<AgentName, Summary> {
  const out = {} as Record<AgentName, Summary>
  ;(['boss', ...SPECIALIST_ORDER] as AgentName[]).forEach((a) => {
    const mine = events.filter((e) => e.agent === a)
    const final = [...mine].reverse().find((e) => e.stop_reason === 'final_result')
    const tools = [...new Set(mine.flatMap((e) => e.tools.map((t) => t.name)))]
    out[a] = {
      agent: a,
      status: mine.length === 0 ? 'unused' : final ? 'done' : 'working',
      steps: mine.length,
      tools: tools.filter((t) => !t.startsWith('ask_')),
      said: final?.said ?? null,
      asked: tools.filter((t) => t.startsWith('ask_')).map((t) => t.replace('ask_', '') as AgentName),
      guard: [...new Set(mine.flatMap((e) => e.guardrail_events))],
    }
  })
  return out
}

/** One card per agent: what it did on this ticket. Agents the boss did not need are shown dimmed, on purpose. */
export default function Summaries({ events, waiting }: { events: AgentEvent[]; waiting: boolean }) {
  const s = summarize(events)
  const order: AgentName[] = ['boss', ...SPECIALIST_ORDER]
  return (
    <section aria-labelledby="sum-h">
      <div className="section-head">
        <h2 id="sum-h">What each agent did</h2>
        <span className="muted small">only the pups the boss needed get called</span>
      </div>
      <div className="summaries">
        {order.map((a) => {
          const m = AGENTS[a]
          const x = s[a]
          return (
            <article key={a} className={`summary ${x.status} ${waiting && x.status === 'unused' ? 'ready' : ''} ${a === 'boss' ? 'wide' : ''}`} style={{ ['--agent' as string]: m.color }}>
              <header>
                <span className="swatch" aria-hidden="true" />
                <b>{m.label}</b>
                <span className="muted small">{m.role}</span>
                <span className={`state ${x.status}`}>
                  {x.status === 'unused' ? (waiting ? 'Ready' : 'Not needed') : x.status === 'working' ? 'Working…' : 'Done'}
                </span>
              </header>
              {x.status === 'unused' ? (
                <p className="muted small">{m.blurb}. {waiting ? 'Waiting for a ticket.' : 'Not called on this ticket.'}</p>
              ) : (
                <>
                  {a === 'boss' ? (
                    <p className="said">
                      Read the ticket, then {x.asked.length ? `sent tasks to ${x.asked.map((n) => AGENTS[n]?.label ?? n).join(', ')}` : 'looked for who to ask'}
                      {x.status === 'done' ? ' and wrote the report above.' : '…'}
                    </p>
                  ) : (
                    <p className="said">{x.said ? firstSentences(x.said, 2, 300) : 'Still reading the ticket…'}</p>
                  )}
                  {x.tools.length > 0 && (
                    <p className="tools">
                      {x.tools.map((t) => (
                        <code key={t}>{t}</code>
                      ))}
                    </p>
                  )}
                  {x.guard.map((g) => (
                    <p key={g} className="guard small">🛡 {g}</p>
                  ))}
                  <p className="muted small">{x.steps} step{x.steps === 1 ? '' : 's'}</p>
                </>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
