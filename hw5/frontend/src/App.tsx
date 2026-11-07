import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from './api'
import Approvals from './components/Approvals'
import Balance from './components/Balance'
import Feed from './components/Feed'
import Field from './components/Field'
import type { FieldHandle } from './components/Field'
import Summaries from './components/Summaries'
import Tickets from './components/Tickets'
import { AGENTS, latestRun, money, phaseOf } from './meta'
import type { AgentEvent, AgentName, Cash, LiveEvent, PaymentsResponse, PendingPayment, TeamResult, Ticket } from './types'

const APPROVER_KEY = 'desk-approver'

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selected, setSelected] = useState<number | null>(() => Number(new URLSearchParams(location.search).get('ticket')) || null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [pay, setPay] = useState<PaymentsResponse | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [reports, setReports] = useState<Record<number, TeamResult>>({})
  const [runningLocal, setRunningLocal] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [offline, setOffline] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<{ amount: number; key: number } | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const [approver, setApprover] = useState(() => {
    try { return localStorage.getItem(APPROVER_KEY) ?? 'Katie Bays' } catch { return 'Katie Bays' }
  })

  const field = useRef<FieldHandle>(null)
  const selectedRef = useRef<number | null>(selected)
  const runningRef = useRef<number | null>(null)
  const cursors = useRef<{ events?: number; live?: number }>({})
  const localThrow = useRef(false)
  selectedRef.current = selected
  runningRef.current = runningLocal

  const applyLive = useCallback((list: LiveEvent[]) => {
    for (const ev of list) {
      if (ev.type === 'run_started' && !localThrow.current && ev.ticket_id !== null) field.current?.throwTicket(ev.ticket_id)
      if (ev.type === 'dispatch') field.current?.dispatch(ev.agent as AgentName, ev.task)
      if (ev.type === 'agent_done') field.current?.done(ev.agent as AgentName, ev.status)
      if (ev.type === 'run_finished') localThrow.current = false
    }
  }, [])

  const applyEvents = useCallback((list: AgentEvent[]) => {
    for (const e of list) {
      if (e.agent === 'human' || e.agent === 'boss') continue
      const used = e.tools.map((t) => t.name).join(', ')
      field.current?.say(e.agent as AgentName, e.stop_reason === 'final_result' && e.said ? e.said : used ? `Used ${used}` : 'Thinking…')
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [t, c, p] = await Promise.all([api.getTickets(), api.getCash(), api.getPayments()])
      setTickets(t.tickets)
      setCash(c)
      setPay(p)
      setOffline(false)
      const id = selectedRef.current
      if (id !== null) {
        const [ev, lv] = await Promise.all([api.getEvents(id, cursors.current.events), api.getLive(id, cursors.current.live)])
        if (selectedRef.current !== id) return
        cursors.current = { events: ev.latest_seq, live: lv.latest_seq }
        if (ev.events.length) {
          setEvents((old) => [...old, ...ev.events.filter((e) => !old.some((o) => o.seq === e.seq))])
          if (runningRef.current === id) applyEvents(ev.events)
        }
        if (lv.events.length && (runningRef.current === id || t.tickets.find((x) => x.id === id)?.running)) applyLive(lv.events)
      }
    } catch {
      setOffline(true)
    }
  }, [applyEvents, applyLive])

  // Poll quickly while the pups are working, slowly otherwise.
  useEffect(() => {
    let stop = false
    let timer = 0
    const loop = async () => {
      await refresh()
      if (!stop) timer = window.setTimeout(loop, runningRef.current !== null ? 900 : 4000)
    }
    void loop()
    return () => {
      stop = true
      window.clearTimeout(timer)
    }
  }, [refresh])

  const select = useCallback(async (id: number) => {
    field.current?.reset()
    localThrow.current = false
    setEvents([])
    setSelected(id)
    selectedRef.current = id
    setError(null)
    try {
      const t = (await api.getTickets()).tickets.find((x) => x.id === id)
      if (t?.running) {
        cursors.current = {} // replay what already happened on this running ticket
      } else {
        const lv = await api.getLive(id)
        cursors.current = { live: lv.latest_seq }
      }
      const ev = await api.getEvents(id)
      cursors.current.events = ev.latest_seq
      setEvents(ev.events)
    } catch {
      setOffline(true)
    }
  }, [])

  // Open the ticket from ?ticket=101, or the first one.
  const first = useRef(true)
  useEffect(() => {
    if (!first.current || tickets.length === 0) return
    first.current = false
    void select(selected ?? tickets[0].id)
  }, [tickets, selected, select])

  const startRun = async (id: number) => {
    setError(null)
    setReports((r) => Object.fromEntries(Object.entries(r).filter(([k]) => Number(k) !== id)))
    try {
      const seqs = await api.getLatestSeqs()
      cursors.current = { events: seqs.events, live: seqs.live }
      setEvents([])
      field.current?.reset()
      localThrow.current = true
      setRunningLocal(id)
      runningRef.current = id
      field.current?.throwTicket(id)
      const res = await api.runTicket(id)
      setReports((r) => ({ ...r, [id]: res.result }))
      await refresh()
      field.current?.finish(
        res.ticket.pending_payments.length || res.ticket.has_draft_reply
          ? 'Report is ready. Over to you for the sign-off.'
          : 'Report is ready.',
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      field.current?.finish('Something went wrong. Check the message above.')
    } finally {
      localThrow.current = false
      setRunningLocal(null)
      runningRef.current = null
      void refresh()
    }
  }

  const rememberApprover = (v: string) => {
    setApprover(v)
    try { localStorage.setItem(APPROVER_KEY, v) } catch { /* private window: fine */ }
  }

  const ticket = tickets.find((t) => t.id === selected) ?? null

  const approve = async (p: PendingPayment) => {
    if (!ticket) return
    setBusy(true)
    setError(null)
    try {
      const closes = !ticket.has_draft_reply && ticket.pending_payments.length === 1
      const res = await api.approvePayment({
        kind: p.kind,
        ref_id: p.ref_id,
        approved_by: approver.trim(),
        ticket_id: ticket.id,
        resolve_ticket: closes,
      })
      setFlash({ amount: res.payment.amount, key: Date.now() })
      await refresh()
      if (closes) field.current?.finish(`Ticket #${ticket.id} is closed. Good dog.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const close = async () => {
    if (!ticket) return
    setBusy(true)
    setError(null)
    try {
      await api.resolveTicket(ticket.id, approver.trim())
      await refresh()
      field.current?.finish(`Ticket #${ticket.id} is closed. Good dog.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setConfirmReset(false)
    setError(null)
    try {
      await api.resetDatabase()
      field.current?.reset()
      setEvents([])
      setReports({})
      setFlash(null)
      cursors.current = {}
      if (selectedRef.current !== null) await select(selectedRef.current)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const run = latestRun(events)
  const phase = ticket ? phaseOf(ticket, runningLocal === ticket.id) : 'open'
  const bossReport = [...run].reverse().find((e) => e.agent === 'boss' && e.stop_reason === 'final_result')?.said ?? reports[ticket?.id ?? -1]?.answer
  const sceneKey = `${ticket?.id}|${phase}|${run.filter((e) => e.stop_reason === 'final_result').map((e) => e.agent).join(',')}`
  useEffect(() => {
    if (!ticket || phase === 'working') return
    const reported = [...new Set(run.filter((e) => e.agent !== 'human' && e.stop_reason === 'final_result').map((e) => e.agent as AgentName))]
    field.current?.restore(
      reported,
      phase === 'resolved' ? `Ticket #${ticket.id} is closed. Good dog.` : phase === 'needs_you' ? 'Waiting on you for the sign-off.' : null,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneKey])
  const resolvedCount = tickets.filter((t) => t.state === 'resolved').length

  return (
    <div className="app">
      <header className="top">
        <div>
          <p className="eyebrow">Campus Customs · MGT 409</p>
          <h1>The Handsome Dan Desk</h1>
          <p className="lede">Toss a ticket to Handsome Dan. He sends his pups to fetch the answers, and you sign off on the money.</p>
        </div>
        <div className="top-right">
          <span className={`pill ${offline ? 'bad' : 'ok'}`}>{offline ? 'Back end offline' : 'Back end connected'}</span>
          {confirmReset ? (
            <span className="reset-confirm">
              Start a fresh run? <button className="btn small danger" onClick={reset}>Yes, reset</button>
              <button className="btn small" onClick={() => setConfirmReset(false)}>Cancel</button>
            </span>
          ) : (
            <button className="btn small" onClick={() => setConfirmReset(true)} disabled={runningLocal !== null}>
              Fresh run
            </button>
          )}
        </div>
      </header>

      {offline && (
        <div className="banner bad" role="alert">
          Can’t reach the back end at {api.API_URL}. Start it from the backend folder with <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}
      {error && (
        <div className="banner bad" role="alert">
          {error} <button className="link" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      <div className="layout">
        <aside className="side">
          <Balance balance={cash?.balance ?? null} asOf={cash?.as_of ?? ''} startingBalance={pay?.starting_balance ?? null} payments={pay?.payments ?? []} flash={flash} />
          <Tickets tickets={tickets} selectedId={selected} workingId={runningLocal} onSelect={select} onRun={startRun} />
          {ticket && phase === 'needs_you' && (
            <Approvals ticket={ticket} approver={approver} onApprover={rememberApprover} busy={busy} onPay={approve} onClose={close} />
          )}
        </aside>

        <main className="main">
          <section className="card scene-card" aria-label="The field">
            <div className="scene-head">
              <h2>{ticket ? `Ticket #${ticket.id}: ${ticket.subject}` : 'Pick a ticket'}</h2>
              <span className={`chip ${phase}`}>
                {phase === 'resolved' ? '✓ Resolved' : phase === 'working' ? 'Dan is on it' : phase === 'needs_you' ? 'Waiting for you' : 'Open'}
              </span>
            </div>
            <Field ref={field} />
            <p className="muted small scene-foot">
              {AGENTS.boss.label} is the boss. Each pup is a specialist agent. {resolvedCount} of {tickets.length} tickets resolved
              {pay ? `, ${money(pay.payments.reduce((s, p) => s + p.amount, 0))} paid out` : ''}.
            </p>
          </section>

          {bossReport && phase !== 'working' && (
            <section className="card report" aria-label="Handsome Dan's report">
              <p className="eyebrow">Handsome Dan’s report</p>
              <p className="report-text">{bossReport}</p>
            </section>
          )}

          <Summaries events={run} waiting={phase === 'open' || phase === 'working'} />
          <Feed events={run} />
        </main>
      </div>
    </div>
  )
}
