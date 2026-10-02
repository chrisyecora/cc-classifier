export type Classification = '' | 'A' | 'B' | 'S'

export interface Transaction {
  transaction_id: string
  date: string
  amount: string
  merchant?: string
  name?: string
  classification: Classification
  percentage?: string
  classified_by?: string
  excluded?: string
  note?: string
  edit_version?: number
}

export interface Totals {
  user_a_name: string
  user_a: string
  user_b_name: string
  user_b: string
  unclassified_count: number
}

export interface Statement {
  month: string
  start_date: string
  end_date: string
  confirmed: boolean
  version: number
  revision: number
  published?: { start_date: string; end_date: string; at: string; totals: Totals }
  has_unpublished_changes: boolean
  totals: Totals
  transactions: Transaction[]
}

export interface AppConfig {
  userPoolId: string
  userPoolClientId: string
  cognitoDomain: string
  redirectUrl: string
}
