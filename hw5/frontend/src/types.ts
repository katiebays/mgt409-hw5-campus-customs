export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface PendingPayment {
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
  payee: string
  due_date: string
  description: string
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  state: 'open' | 'resolved'
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  notes: string | null
  created_at: string
  running: boolean
  pending_payments: PendingPayment[]
  has_draft_reply: boolean
  can_close: boolean
}

export interface TicketsResponse {
  tickets: Ticket[]
  open: number
  resolved: number
}

export interface ToolUse {
  name: string
  args: string
  result: string
}

export interface AgentEvent {
  seq: number
  timestamp: string
  run_id: string
  ticket_id: number | null
  agent: string
  agent_run_id: string
  parent_agent_run_id: string | null
  iteration: number
  said: string | null
  tools: ToolUse[]
  guardrail_events: string[]
  stop_reason: string
  approver: string | null
}

export interface EventsResponse {
  events: AgentEvent[]
  total: number
  latest_seq: number
  running_tickets: number[]
}

export interface LiveEvent {
  seq: number
  timestamp: string
  type: 'run_started' | 'dispatch' | 'agent_done' | 'run_finished'
  ticket_id: number | null
  run_id: string
  agent: string
  task: string | null
  status: string | null
}

export interface LiveResponse {
  events: LiveEvent[]
  latest_seq: number
  running_tickets: number[]
}

export interface TicketOutcome {
  ticket_id: number
  status: string
  summary: string
  handled_by: string[]
  needs_human: string[]
}

export interface TeamResult {
  answer: string
  outcomes: TicketOutcome[]
  needs_human: string[]
}

export interface RunTicketResponse {
  run_id: string
  ticket: Ticket
  result: TeamResult
}

export interface Payment {
  id: number
  kind: string
  ref_id: number | null
  amount: number
  account: string
  paid_at: string
  approved_by: string
  payee: string | null
  description: string | null
  ticket_id: number | null
}

export interface PaymentsResponse {
  payments: Payment[]
  starting_balance: number
  checking_balance: number
}

export interface Cash {
  account: string
  balance: number
  as_of: string
}
