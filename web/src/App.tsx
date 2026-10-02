import { useCallback, useEffect, useState } from 'react'
import { Hub } from 'aws-amplify/utils'
import { getCurrentUser, signInWithRedirect, signOut } from 'aws-amplify/auth'
import { getStatement, publish, savePeriod, updateTransaction } from './api'
import type { Classification, Statement, Transaction } from './types'

function previousMonth(): string {
  const today = new Date()
  return new Date(Date.UTC(today.getFullYear(), today.getMonth() - 1, 1)).toISOString().slice(0, 7)
}

function TransactionRow({ transaction, statement, onSaved, onError }: {
  transaction: Transaction
  statement: Statement
  onSaved: () => Promise<void>
  onError: (message: string) => void
}) {
  const [classification, setClassification] = useState<Classification>(transaction.classification || '')
  const [excluded, setExcluded] = useState(transaction.excluded === 'true')
  const [percentage, setPercentage] = useState(transaction.percentage || '50')
  const [shareUser, setShareUser] = useState<'A' | 'B'>(transaction.classified_by === statement.totals.user_b_name ? 'B' : 'A')
  const [note, setNote] = useState(transaction.note || '')
  const [saving, setSaving] = useState(false)
  const changed = classification !== (transaction.classification || '') || excluded !== (transaction.excluded === 'true') ||
    note !== (transaction.note || '') || (classification === 'S' && (percentage !== (transaction.percentage || '50') ||
    shareUser !== (transaction.classified_by === statement.totals.user_b_name ? 'B' : 'A')))

  async function save() {
    setSaving(true)
    onError('')
    try {
      await updateTransaction(transaction.transaction_id, {
        version: transaction.edit_version || 0,
        classification,
        excluded,
        note,
        percentage: classification === 'S' ? percentage : null,
        share_user: classification === 'S' ? shareUser : null,
      })
      await onSaved()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Could not save transaction')
    } finally {
      setSaving(false)
    }
  }

  return <tr className={excluded ? 'excluded' : ''}>
    <td>{transaction.date}</td>
    <td><strong>{transaction.merchant || transaction.name || 'Unknown merchant'}</strong><small>{transaction.transaction_id}</small></td>
    <td className="amount">${Number(transaction.amount).toFixed(2)}</td>
    <td><select aria-label={`Classification for ${transaction.merchant || transaction.transaction_id}`} value={classification} onChange={e => setClassification(e.target.value as Classification)}>
      <option value="">Unclassified</option><option value="A">{statement.totals.user_a_name}</option>
      <option value="B">{statement.totals.user_b_name}</option><option value="S">Shared</option>
    </select>
      {classification === 'S' && <div className="split"><select aria-label="Person paying percentage" value={shareUser} onChange={e => setShareUser(e.target.value as 'A' | 'B')}>
        <option value="A">{statement.totals.user_a_name}</option><option value="B">{statement.totals.user_b_name}</option>
      </select><input aria-label="Share percentage" type="number" min="0" max="100" step="0.01" value={percentage} onChange={e => setPercentage(e.target.value)} />%</div>}
    </td>
    <td><label className="checkbox"><input type="checkbox" checked={excluded} onChange={e => setExcluded(e.target.checked)} /> Ignore</label></td>
    <td><input aria-label={`Note for ${transaction.merchant || transaction.transaction_id}`} type="text" maxLength={200} value={note} onChange={e => setNote(e.target.value)} /></td>
    <td><button disabled={!changed || saving} onClick={save}>{saving ? 'Saving…' : 'Save'}</button></td>
  </tr>
}

export default function App() {
  const [signedIn, setSignedIn] = useState(false)
  const [checking, setChecking] = useState(true)
  const [month, setMonth] = useState(previousMonth)
  const [statement, setStatement] = useState<Statement | null>(null)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const checkAuth = useCallback(async () => {
    try { await getCurrentUser(); setSignedIn(true) } catch { setSignedIn(false) }
    setChecking(false)
  }, [])
  useEffect(() => {
    const cancel = Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signedIn' || payload.event === 'signedOut' || payload.event === 'signInWithRedirect_failure') void checkAuth()
    })
    void checkAuth()
    return cancel
  }, [checkAuth])

  const load = useCallback(async () => {
    if (!signedIn || !/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) return
    setBusy(true); setError('')
    try {
      const data = await getStatement(month)
      setStatement(data); setStart(data.start_date); setEnd(data.end_date)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not load statement'); setStatement(null) }
    finally { setBusy(false) }
  }, [month, signedIn])
  useEffect(() => { void load() }, [load])

  async function saveDates() {
    if (!statement) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await savePeriod(month, start, end, statement.version)
      setStatement(updated); setStart(updated.start_date); setEnd(updated.end_date)
      setNotice('Statement dates confirmed.')
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not save dates') }
    finally { setBusy(false) }
  }

  async function publishStatement() {
    if (!statement || !window.confirm(`Publish settlement ${statement.revision + 1} for ${month} to Discord?`)) return
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await publish(month, statement.version)
      setStatement(updated); setNotice(`Settlement revision ${updated.revision} posted to Discord.`)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not publish settlement') }
    finally { setBusy(false) }
  }

  if (checking) return <main className="shell"><p>Checking sign in…</p></main>
  if (!signedIn) return <main className="shell login"><h1>Statement Review</h1><p>Sign in to review and publish credit card settlements.</p><button className="primary" onClick={() => void signInWithRedirect()}>Sign in</button></main>

  return <main className="shell">
    <header><div><p className="eyebrow">Credit card tracker</p><h1>Statement Review</h1></div><button onClick={() => void signOut()}>Sign out</button></header>
    <section className="toolbar"><label>Statement month <input type="month" value={month} onChange={e => setMonth(e.target.value)} /></label><button onClick={() => void load()} disabled={busy}>Refresh</button></section>
    {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
    {statement && <>
      <section className="panel"><div className="section-title"><h2>Billing period</h2><span className={statement.confirmed ? 'tag confirmed' : 'tag'}>{statement.confirmed ? 'Confirmed' : 'Draft'}</span></div>
        <div className="date-controls"><label>Start <input type="date" value={start} onChange={e => setStart(e.target.value)} /></label><label>End <input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label><button className="primary" onClick={() => void saveDates()} disabled={busy || (statement.confirmed && start === statement.start_date && end === statement.end_date)}>Confirm dates</button></div>
        <p className="hint">Check these dates against the credit card statement before publishing. The next period starts the day after this one ends.</p>
      </section>
      <section className="cards"><div><span>{statement.totals.user_a_name} owes</span><strong>${statement.totals.user_a}</strong></div><div><span>{statement.totals.user_b_name} owes</span><strong>${statement.totals.user_b}</strong></div><div><span>Unclassified</span><strong>{statement.totals.unclassified_count}</strong></div><div><span>Transactions</span><strong>{statement.transactions.length}</strong></div></section>
      <section className="panel"><div className="section-title"><h2>Transactions</h2><span>{statement.transactions.length} in this period</span></div>
        <div className="table-wrap"><table><thead><tr><th>Date</th><th>Merchant</th><th>Amount</th><th>Classification</th><th>Status</th><th>Note</th><th></th></tr></thead><tbody>
          {statement.transactions.map(t => <TransactionRow key={`${t.transaction_id}:${t.edit_version || 0}`} transaction={t} statement={statement} onSaved={load} onError={setError} />)}
        </tbody></table></div>
        {!statement.transactions.length && <p>No transactions in this date range.</p>}
      </section>
      <section className="panel publication"><div><h2>Discord settlement</h2><p>{statement.revision ? `Published revision ${statement.revision} on ${new Date(statement.published!.at).toLocaleString()}.` : 'No settlement published yet.'}</p>
        {statement.has_unpublished_changes && <p className="changed">This statement has unpublished changes.</p>}</div>
        <button className="primary" onClick={() => void publishStatement()} disabled={busy || !statement.confirmed || statement.totals.unclassified_count > 0 || (statement.revision > 0 && !statement.has_unpublished_changes)}>{statement.revision ? 'Publish revision' : 'Publish settlement'}</button>
      </section>
    </>}
  </main>
}
