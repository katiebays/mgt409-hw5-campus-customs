import { useImperativeHandle, useRef, useState } from 'react'
import type { Ref } from 'react'
import Dan, { TennisBall } from './Dan'
import type { DanMode } from './Dan'
import { AGENTS, clip } from '../meta'
import type { AgentName } from '../types'

/** What App tells the field to show. The field turns each command into a throw, a run, or a fetch. */
export interface FieldHandle {
  throwTicket: (ticketId: number) => void
  dispatch: (agent: AgentName, task: string | null) => void
  done: (agent: AgentName, status: string | null) => void
  say: (agent: AgentName, text: string) => void
  finish: (text: string) => void
  restore: (doneAgents: AgentName[], bossText: string | null) => void
  reset: () => void
}

interface Dog {
  x: number
  y: number
  mode: DanMode
  bubble: string | null
}
interface Ball {
  id: number
  x: number
  y: number
  label: string | null
}

// Positions are percentages of the field, so the scene scales with the page.
const DESK = { x: 8, y: 30 }
const HOME: Record<AgentName, { x: number; y: number }> = {
  boss: { x: 50, y: 25 },
  inventory: { x: 13, y: 80 },
  accounting: { x: 38, y: 80 },
  facilities: { x: 62, y: 80 },
  customer_service: { x: 87, y: 80 },
}
const SPOT = (a: AgentName) => ({ x: HOME[a].x, y: 56 })
const MOVE_MS = 900

const initialDogs = (): Record<AgentName, Dog> =>
  (Object.keys(HOME) as AgentName[]).reduce(
    (acc, a) => ({ ...acc, [a]: { ...HOME[a], mode: 'idle' as DanMode, bubble: null } }),
    {} as Record<AgentName, Dog>,
  )

export default function Field({ ref }: { ref?: Ref<FieldHandle> }) {
  const [dogs, setDogs] = useState<Record<AgentName, Dog>>(initialDogs)
  const [balls, setBalls] = useState<Ball[]>([])
  const [bossHolds, setBossHolds] = useState(false)
  const [catchKey, setCatchKey] = useState(0)
  const ballId = useRef(0)
  const timers = useRef<number[]>([])

  const later = (fn: () => void, ms: number) => {
    timers.current.push(window.setTimeout(fn, ms))
  }
  const patch = (a: AgentName, p: Partial<Dog>) => setDogs((d) => ({ ...d, [a]: { ...d[a], ...p } }))
  const addBall = (x: number, y: number, label: string | null) => {
    const id = (ballId.current += 1)
    setBalls((b) => [...b, { id, x, y, label }])
    return id
  }
  const moveBall = (id: number, x: number, y: number) => setBalls((b) => b.map((k) => (k.id === id ? { ...k, x, y } : k)))
  const dropBall = (id: number) => setBalls((b) => b.filter((k) => k.id !== id))

  useImperativeHandle(ref, () => ({
    throwTicket(ticketId) {
      // The ticket leaves the desk as a tennis ball; the boss sprints out, grabs it and trots home.
      const id = addBall(DESK.x, DESK.y, `#${ticketId}`)
      later(() => moveBall(id, 36, 32), 60)
      later(() => patch('boss', { x: 36, y: 32, mode: 'running', bubble: null }), 350)
      later(() => {
        dropBall(id)
        setBossHolds(true)
        patch('boss', { ...HOME.boss, mode: 'running', bubble: `Ticket #${ticketId}. Let me see who should take this.` })
      }, 350 + MOVE_MS)
      later(() => patch('boss', { mode: 'working' }), 350 + MOVE_MS * 2)
    },
    dispatch(agent, task) {
      if (agent === 'boss') return
      // The boss throws the ball toward a specialist, and that pup races to fetch it.
      const spot = SPOT(agent)
      const id = addBall(HOME.boss.x, HOME.boss.y + 8, null)
      later(() => moveBall(id, spot.x, spot.y), 60)
      patch('boss', { mode: 'working', bubble: `${AGENTS[agent].label}: ${clip(task ?? 'take this one', 110)}` })
      later(() => patch(agent, { x: spot.x, y: spot.y, mode: 'running', bubble: null }), 300)
      later(() => {
        dropBall(id)
        patch(agent, { mode: 'working', bubble: 'Got it. Looking into it…' })
      }, 300 + MOVE_MS)
    },
    done(agent, status) {
      if (agent === 'boss') return
      // The pup runs home and the ball flies back to the boss, who catches it.
      const blocked = status === 'blocked'
      const id = addBall(dogs[agent].x, dogs[agent].y - 6, null)
      patch(agent, { ...HOME[agent], mode: 'running' })
      later(() => moveBall(id, HOME.boss.x, HOME.boss.y + 6), 60)
      later(() => {
        dropBall(id)
        setCatchKey((k) => k + 1)
        patch(agent, { mode: blocked ? 'blocked' : 'done', bubble: null })
        patch('boss', { mode: 'working', bubble: `${AGENTS[agent].label} is back with a report.` })
      }, MOVE_MS)
    },
    say(agent, text) {
      patch(agent, { bubble: clip(text, 120) })
    },
    finish(text) {
      setBossHolds(false)
      patch('boss', { mode: 'idle', bubble: text })
    },
    restore(doneAgents, bossText) {
      // Re-open a ticket that was already worked: pups that reported show a check, the boss says where it stands.
      setBalls([])
      setBossHolds(false)
      setDogs(() => {
        const next = initialDogs()
        doneAgents.forEach((a) => {
          if (a !== 'boss') next[a] = { ...next[a], mode: 'done' }
        })
        next.boss = { ...next.boss, bubble: bossText }
        return next
      })
    },
    reset() {
      timers.current.forEach((t) => window.clearTimeout(t))
      timers.current = []
      setDogs(initialDogs())
      setBalls([])
      setBossHolds(false)
    },
  }))

  return (
    <div className="field" aria-label="The field: Handsome Dan and his pups">
      <div className="field-lines" aria-hidden="true" />
      <div className="desk" style={{ left: `${DESK.x}%`, top: `${DESK.y}%` }} aria-hidden="true">
        <span className="desk-tray" />
        <span className="desk-label">Ticket desk</span>
      </div>

      {(Object.keys(HOME) as AgentName[]).map((a) => {
        const d = dogs[a]
        const meta = AGENTS[a]
        const isBoss = a === 'boss'
        return (
          <div
            key={a}
            className={`dog ${isBoss ? 'boss' : ''} ${d.mode}`}
            style={{ left: `${d.x}%`, top: `${d.y}%` }}
          >
            {d.bubble && <div className={`bubble ${isBoss ? 'bubble-boss' : ''}`} style={{ borderColor: meta.color }}>{d.bubble}</div>}
            <Dan
              fur={meta.fur}
              bandana={meta.color}
              size={isBoss ? 124 : 88}
              mode={d.mode}
              carry={isBoss ? bossHolds : false}
              prop={meta.prop}
            />
            <div className="dog-name" style={{ background: meta.color }}>{meta.label}</div>
            {isBoss && catchKey > 0 && <span key={catchKey} className="catch-flash" />}
          </div>
        )
      })}

      {balls.map((b) => (
        <div key={b.id} className="ball" style={{ left: `${b.x}%`, top: `${b.y}%` }}>
          <div className="ball-arc">
            <TennisBall size={30} />
            {b.label && <span className="ball-tag">{b.label}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

