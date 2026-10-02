import { fetchAuthSession } from 'aws-amplify/auth'
import type { Statement } from './types'

async function request<T>(path: string, method = 'GET', body?: object): Promise<T> {
  const session = await fetchAuthSession()
  const token = session.tokens?.idToken?.toString()
  if (!token) throw new Error('Please sign in again.')
  const response = await fetch(`/api${path}`, {
    method,
    headers: { Authorization: token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || (response.status === 401 ? 'Session expired. Please sign in again.' : `Request failed (${response.status})`))
  return data as T
}

export const getStatement = (month: string) => request<Statement>(`/statements/${month}`)
export const savePeriod = (month: string, start_date: string, end_date: string, version: number) =>
  request<Statement>(`/statements/${month}`, 'PUT', { start_date, end_date, version })
export const publish = (month: string, version: number) =>
  request<Statement>(`/statements/${month}/publish`, 'POST', { version })
export const updateTransaction = (id: string, body: object) => request(`/transactions/${encodeURIComponent(id)}`, 'PATCH', body)
