/** API types matching backend docs/API.md */

export type TokenResponse = {
  access_token: string
  token_type: string
}

export type User = {
  id: number
  username: string
  credits_balance: number
}

export type LeaderboardEntry = {
  username: string
  credits_balance: number
  rank: number
}

export type LeaderboardResponse = {
  top: LeaderboardEntry[]
  current_user: LeaderboardEntry | null
}

export enum WagerStatus {
  PENDING = 'PENDING',
  PENDING_DATA = 'PENDING_DATA',
  WIN = 'WIN',
  LOSE = 'LOSE',
}

export type Wager = {
  id: number
  amount: number
  status: WagerStatus | string
  forecast_date: string | null
  target: string | null
  bucket_low: number | null
  bucket_high: number | null
  created_at: string | null
  wager_kind?: 'BUCKET' | 'OVER_UNDER' | string
  direction?: 'OVER' | 'UNDER' | string | null
  predicted_value?: number | null
  base_payout_multiplier?: number | null
  winnings?: number | null
}

export type PlaceWagerBody = {
  forecast_date: string
  target: string
  amount: number
  wager_kind: 'BUCKET' | 'OVER_UNDER'
  bucket_value?: number
  direction?: 'OVER' | 'UNDER'
  predicted_value?: number
}

export type PlaceWagerResponse = {
  id: number
  status: string
  message: string
}

export type DailyStatusResponse = {
  status: 'AVAILABLE' | 'CLAIMED'
}

export type DailyClaimResponse = {
  message: string
  added_credits: number
  new_balance: number
  status: 'CLAIMED'
}

export type OddsOption = {
  id: number
  forecast_date: string
  target: string
  bucket_name: string
  bucket_low: number
  bucket_high: number
  probability: number | null
  base_payout_multiplier: number
  jackpot_multiplier: number
}

export const TARGET_LABELS: Record<string, string> = {
  high_temp: 'High temperature (°F)',
  avg_wind_speed: 'Avg wind speed (mph)',
  precipitation: 'Precipitation (in)',
}
