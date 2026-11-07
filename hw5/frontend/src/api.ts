import type {
  Cash,
  EventsResponse,
  LiveResponse,
  PaymentsResponse,
  RunTicketResponse,
  Ticket,
  TicketsResponse,
} from './types'

/** The back end. Change it with VITE_API_URL; by default it is http://localhost:8000. */
export const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* keep the status text */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const getTickets = () => request<TicketsResponse>('/api/tickets')
export const getCash = () => request<Cash>('/api/cash')
export const getPayments = () => request<PaymentsResponse>('/api/payments')
export const getEvents = (ticketId: number, sinceSeq?: number) =>
  request<EventsResponse>(
    `/api/events?limit=500&ticket_id=${ticketId}${sinceSeq !== undefined ? `&since_seq=${sinceSeq}` : ''}`,
  )
export const getLive = (ticketId: number, sinceSeq?: number) =>
  request<LiveResponse>(`/api/live?ticket_id=${ticketId}${sinceSeq !== undefined ? `&since_seq=${sinceSeq}` : ''}`)
export const getLatestSeqs = () =>
  Promise.all([request<EventsResponse>('/api/events?limit=1'), request<LiveResponse>('/api/live')]).then(
    ([e, l]) => ({ events: e.latest_seq, live: l.latest_seq }),
  )

export const runTicket = (id: number) => post<RunTicketResponse>(`/api/tickets/${id}/run`)
export const approvePayment = (body: {
  kind: 'invoice' | 'rent'
  ref_id: number
  approved_by: string
  ticket_id: number
  resolve_ticket: boolean
}) => post<{ ok: boolean; payment: { amount: number }; checking_balance: number; ticket: Ticket | null }>('/api/approve', body)
export const resolveTicket = (id: number, approved_by: string) =>
  post<{ ok: boolean; ticket: Ticket }>(`/api/tickets/${id}/resolve`, { approved_by })
export const resetDatabase = () => post<{ ok: boolean; checking_balance: number }>('/api/reset')
