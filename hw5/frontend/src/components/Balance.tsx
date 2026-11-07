import { useEffect, useRef, useState } from 'react'
import { money } from '../meta'
import type { Payment } from '../types'

function useCountUp(target: number | null): number | null {
  const [shown, setShown] = useState<number | null>(target)
  const from = useRef<number | null>(target)
  useEffect(() => {
    if (target === null) return
    if (from.current === null || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      from.current = target
      setShown(target)
      return
    }
    const start = from.current
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / 1100)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(start + (target - start) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    // A background tab pauses animation frames. Make sure the final number still lands.
    const settle = window.setTimeout(() => {
      cancelAnimationFrame(raf)
      from.current = target
      setShown(target)
    }, 1400)
    return () => {
      cancelAnimationFrame(raf)
      window.clearTimeout(settle)
      from.current = target
    }
  }, [target])
  return shown
}

/** The balance after each payment, drawn as a step line that re-draws whenever a payment is approved. */
function Flow({ start, payments }: { start: number; payments: Payment[] }) {
  const values = [start]
  payments.forEach((p) => values.push(Math.round((values[values.length - 1] - p.amount) * 100) / 100))
  const w = 280
  const h = 74
  const pad = 10
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const span = max - min || 1
  const x = (i: number) => pad + (values.length === 1 ? (w - 2 * pad) / 2 : (i * (w - 2 * pad)) / (values.length - 1))
  const y = (v: number) => pad + (1 - (v - min) / span) * (h - 2 * pad)
  const d = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="flow" role="img" aria-label={`Checking balance over time: ${values.map(money).join(', then ')}`}>
      <line x1={pad} x2={w - pad} y1={y(0)} y2={y(0)} className="flow-zero" />
      <path key={values.join('-')} d={d} className="flow-line" pathLength={1} />
      {values.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r={i === values.length - 1 ? 5 : 3.5} className={i === values.length - 1 ? 'flow-dot now' : 'flow-dot'} />
      ))}
    </svg>
  )
}

export default function Balance({
  balance,
  asOf,
  startingBalance,
  payments,
  flash,
}: {
  balance: number | null
  asOf: string
  startingBalance: number | null
  payments: Payment[]
  flash: { amount: number; key: number } | null
}) {
  const shown = useCountUp(balance)
  return (
    <section className="card balance" aria-label="Checking balance">
      <div className="balance-top">
        <div>
          <p className="eyebrow">Checking</p>
          <p className="balance-num" aria-live="polite">{shown === null ? '…' : money(shown)}</p>
          <p className="muted small">as of {asOf || '…'}</p>
        </div>
        <div className="coin-stage" aria-hidden="true">
          {flash && (
            <div key={flash.key} className="coins">
              <span className="coin-amount">−{money(flash.amount)}</span>
              {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                <span key={i} className="coin" style={{ ['--i' as string]: i }} />
              ))}
            </div>
          )}
        </div>
      </div>
      {startingBalance !== null && <Flow start={startingBalance} payments={payments} />}
      <ul className="ledger" aria-label="Payments">
        {payments.length === 0 && <li className="muted small">No payments yet. Money only moves when you approve it.</li>}
        {payments.map((p) => (
          <li key={p.id}>
            <span className="ledger-amt">−{money(p.amount)}</span>
            <span className="ledger-what">
              {p.kind === 'rent' ? 'Rent' : 'Purchase'} · {p.payee ?? 'payee'}
              {p.ticket_id ? ` · #${p.ticket_id}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
