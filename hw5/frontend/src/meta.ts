import type { AgentEvent, AgentName, Ticket } from './types'

/** Each agent is its own Handsome Dan: a different bandana, prop and coat, so you can tell them apart at a glance. */
export const AGENTS: Record<
  AgentName,
  { label: string; role: string; color: string; fur: string; prop: string; blurb: string }
> = {
  boss: { label: 'Handsome Dan', role: 'Boss', color: '#00356b', fur: '#f4ead8', prop: '', blurb: 'Reads the ticket and sends the right pups' },
  inventory: { label: 'Inventory Dan', role: 'Stock and reorders', color: '#1f7a4d', fur: '#e8d3b0', prop: '📋', blurb: 'Counts shelves, proposes reorders' },
  accounting: { label: 'Accounting Dan', role: 'Cash and bills', color: '#a8741a', fur: '#efe0c6', prop: '🧮', blurb: 'Checks cash, prepares payments' },
  facilities: { label: 'Facilities Dan', role: 'Lease and rent', color: '#b4531f', fur: '#dcc6a3', prop: '🔑', blurb: 'Checks rent notices against the lease' },
  customer_service: { label: 'Service Dan', role: 'Customers and prices', color: '#1b8a93', fur: '#f0e2cc', prop: '🎧', blurb: 'Quotes prices, drafts replies' },
}

export const SPECIALIST_ORDER: AgentName[] = ['inventory', 'accounting', 'facilities', 'customer_service']

export const TICKET_TYPE: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Discount request',
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

export type Phase = 'open' | 'working' | 'needs_you' | 'resolved'

export function phaseOf(t: Ticket, working: boolean): Phase {
  if (t.state === 'resolved') return 'resolved'
  if (working || t.running) return 'working'
  if (t.status === 'open') return 'open'
  return 'needs_you'
}

export const PHASE_LABEL: Record<Phase, string> = {
  open: 'Open',
  working: 'Dan is on it',
  needs_you: 'Waiting for you',
  resolved: 'Resolved',
}

/** The draft customer reply an agent saved in the ticket notes, if any. */
export function draftReply(notes: string | null): string | null {
  if (!notes) return null
  const start = notes.lastIndexOf('DRAFT REPLY')
  if (start < 0) return null
  const rest = notes.slice(start)
  const next = rest.search(/\n\[\d{4}-\d{2}-\d{2} /)
  return (next < 0 ? rest : rest.slice(0, next)).trim()
}

/** Only the newest run of a ticket (plus the human actions after it): older runs belong to an earlier fresh start. */
export function latestRun(events: AgentEvent[]): AgentEvent[] {
  const agentEvents = events.filter((e) => e.agent !== 'human')
  if (!agentEvents.length) return events.filter((e) => e.agent === 'human')
  const runId = agentEvents[agentEvents.length - 1].run_id
  const first = agentEvents.find((e) => e.run_id === runId)!.seq
  return events.filter((e) => e.seq >= first)
}

export function shortTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })
}

export function clip(text: string, n: number): string {
  return text.length > n ? text.slice(0, n - 1).trimEnd() + '…' : text
}

/** The first couple of sentences of a longer text, so a card reads as a summary. */
export function firstSentences(text: string, count: number, max: number): string {
  const parts = text.replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s+/)
  return clip(parts.slice(0, count).join(' '), max)
}
