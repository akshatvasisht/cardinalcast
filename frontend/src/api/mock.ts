/**
 * Mock data returned by the API client when VITE_DEV_BYPASS_AUTH=true.
 * Used for screenshots and UI development without a running backend.
 * All dates are computed relative to today so screenshots stay current.
 */

import type { Wager, OddsOption, LeaderboardResponse, DailyStatusResponse, DailyClaimResponse } from './types'
import { WagerStatus } from './types'

// ── Date helpers ───────────────────────────────────────────────────────────
function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function daysAhead(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

function daysAgoISO(n: number, hour = 18): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(hour, 0, 0, 0)
  return d.toISOString()
}

// ── User ───────────────────────────────────────────────────────────────────
export const MOCK_USER = {
  id: 1,
  username: 'dev_user',
  credits_balance: 2_340,
}

// ── Wagers ─────────────────────────────────────────────────────────────────
// Spread across the past 14 days with a mix of targets, kinds, and statuses.
export const MOCK_WAGERS: Wager[] = [
  {
    id: 1,
    forecast_date: daysAgo(13),
    target: 'high_temp',
    wager_kind: 'BUCKET',
    bucket_low: 50, bucket_high: 60,
    amount: 50,
    status: WagerStatus.WIN,
    winnings: 90,
    base_payout_multiplier: 1.8,
    created_at: daysAgoISO(14, 18),
    direction: null, predicted_value: null,
  },
  {
    id: 2,
    forecast_date: daysAgo(11),
    target: 'avg_wind_speed',
    wager_kind: 'OVER_UNDER',
    bucket_low: null, bucket_high: null,
    direction: 'OVER', predicted_value: 12,
    amount: 25,
    status: WagerStatus.LOSE,
    winnings: 0,
    base_payout_multiplier: 2.4,
    created_at: daysAgoISO(12, 20),
  },
  {
    id: 3,
    forecast_date: daysAgo(9),
    target: 'precipitation',
    wager_kind: 'BUCKET',
    bucket_low: 0, bucket_high: 0.01,
    amount: 100,
    status: WagerStatus.WIN,
    winnings: 150,
    base_payout_multiplier: 1.5,
    created_at: daysAgoISO(10, 17),
    direction: null, predicted_value: null,
  },
  {
    id: 4,
    forecast_date: daysAgo(7),
    target: 'high_temp',
    wager_kind: 'OVER_UNDER',
    bucket_low: null, bucket_high: null,
    direction: 'UNDER', predicted_value: 55,
    amount: 75,
    status: WagerStatus.WIN,
    winnings: 120,
    base_payout_multiplier: 1.6,
    created_at: daysAgoISO(8, 21),
  },
  {
    id: 5,
    forecast_date: daysAgo(6),
    target: 'avg_wind_speed',
    wager_kind: 'BUCKET',
    bucket_low: 10, bucket_high: 15,
    amount: 50,
    status: WagerStatus.LOSE,
    winnings: 0,
    base_payout_multiplier: 2.0,
    created_at: daysAgoISO(7, 19),
    direction: null, predicted_value: null,
  },
  {
    id: 6,
    forecast_date: daysAgo(4),
    target: 'high_temp',
    wager_kind: 'BUCKET',
    bucket_low: 60, bucket_high: 70,
    amount: 150,
    status: WagerStatus.WIN,
    winnings: 465,
    base_payout_multiplier: 3.1,
    created_at: daysAgoISO(5, 16),
    direction: null, predicted_value: null,
  },
  {
    id: 7,
    forecast_date: daysAgo(3),
    target: 'precipitation',
    wager_kind: 'OVER_UNDER',
    bucket_low: null, bucket_high: null,
    direction: 'OVER', predicted_value: 0.1,
    amount: 30,
    status: WagerStatus.LOSE,
    winnings: 0,
    base_payout_multiplier: 1.8,
    created_at: daysAgoISO(4, 22),
  },
  {
    id: 8,
    forecast_date: daysAgo(2),
    target: 'avg_wind_speed',
    wager_kind: 'BUCKET',
    bucket_low: 5, bucket_high: 10,
    amount: 75,
    status: WagerStatus.PENDING_DATA,
    winnings: null,
    base_payout_multiplier: 2.2,
    created_at: daysAgoISO(3, 18),
    direction: null, predicted_value: null,
  },
  {
    id: 9,
    forecast_date: daysAgo(1),
    target: 'high_temp',
    wager_kind: 'BUCKET',
    bucket_low: 50, bucket_high: 60,
    amount: 100,
    status: WagerStatus.PENDING_DATA,
    winnings: null,
    base_payout_multiplier: 1.9,
    created_at: daysAgoISO(2, 20),
    direction: null, predicted_value: null,
  },
  {
    id: 10,
    forecast_date: daysAgo(0),
    target: 'precipitation',
    wager_kind: 'OVER_UNDER',
    bucket_low: null, bucket_high: null,
    direction: 'OVER', predicted_value: 0.25,
    amount: 50,
    status: WagerStatus.PENDING,
    winnings: null,
    base_payout_multiplier: 2.5,
    created_at: daysAgoISO(0, 9),
  },
  {
    id: 11,
    forecast_date: daysAgo(0),
    target: 'high_temp',
    wager_kind: 'BUCKET',
    bucket_low: 60, bucket_high: 70,
    amount: 80,
    status: WagerStatus.PENDING,
    winnings: null,
    base_payout_multiplier: 1.7,
    created_at: daysAgoISO(0, 10),
    direction: null, predicted_value: null,
  },
]

// ── Odds ───────────────────────────────────────────────────────────────────
// Five upcoming forecast dates, three targets each, five buckets each.

type BucketTemplate = Omit<OddsOption, 'id' | 'forecast_date'>

const HIGH_TEMP_BUCKETS: BucketTemplate[] = [
  { target: 'high_temp', bucket_name: 'Below 40°F',  bucket_low: 0,  bucket_high: 40,  probability: 0.04, base_payout_multiplier: 12.5, jackpot_multiplier: 1.5 },
  { target: 'high_temp', bucket_name: '40–50°F',     bucket_low: 40, bucket_high: 50,  probability: 0.18, base_payout_multiplier: 3.1,  jackpot_multiplier: 1.1 },
  { target: 'high_temp', bucket_name: '50–60°F',     bucket_low: 50, bucket_high: 60,  probability: 0.38, base_payout_multiplier: 1.6,  jackpot_multiplier: 1.0 },
  { target: 'high_temp', bucket_name: '60–70°F',     bucket_low: 60, bucket_high: 70,  probability: 0.30, base_payout_multiplier: 2.1,  jackpot_multiplier: 1.0 },
  { target: 'high_temp', bucket_name: 'Above 70°F',  bucket_low: 70, bucket_high: 120, probability: 0.10, base_payout_multiplier: 5.8,  jackpot_multiplier: 1.3 },
]

const WIND_BUCKETS: BucketTemplate[] = [
  { target: 'avg_wind_speed', bucket_name: 'Calm (0–5 mph)',    bucket_low: 0,  bucket_high: 5,   probability: 0.15, base_payout_multiplier: 3.8,  jackpot_multiplier: 1.1 },
  { target: 'avg_wind_speed', bucket_name: 'Light (5–10 mph)',  bucket_low: 5,  bucket_high: 10,  probability: 0.35, base_payout_multiplier: 1.8,  jackpot_multiplier: 1.0 },
  { target: 'avg_wind_speed', bucket_name: 'Moderate (10–15)', bucket_low: 10, bucket_high: 15,  probability: 0.28, base_payout_multiplier: 2.2,  jackpot_multiplier: 1.0 },
  { target: 'avg_wind_speed', bucket_name: 'Brisk (15–25)',     bucket_low: 15, bucket_high: 25,  probability: 0.17, base_payout_multiplier: 3.5,  jackpot_multiplier: 1.1 },
  { target: 'avg_wind_speed', bucket_name: 'Windy (25+ mph)',   bucket_low: 25, bucket_high: 100, probability: 0.05, base_payout_multiplier: 9.2,  jackpot_multiplier: 1.5 },
]

const PRECIP_BUCKETS: BucketTemplate[] = [
  { target: 'precipitation', bucket_name: 'None (0.00 in)',          bucket_low: 0,    bucket_high: 0.01, probability: 0.45, base_payout_multiplier: 1.4,  jackpot_multiplier: 1.0 },
  { target: 'precipitation', bucket_name: 'Trace (0.01–0.10 in)',    bucket_low: 0.01, bucket_high: 0.10, probability: 0.25, base_payout_multiplier: 2.3,  jackpot_multiplier: 1.0 },
  { target: 'precipitation', bucket_name: 'Light (0.10–0.25 in)',    bucket_low: 0.10, bucket_high: 0.25, probability: 0.15, base_payout_multiplier: 3.8,  jackpot_multiplier: 1.1 },
  { target: 'precipitation', bucket_name: 'Moderate (0.25–0.50 in)', bucket_low: 0.25, bucket_high: 0.50, probability: 0.10, base_payout_multiplier: 5.5,  jackpot_multiplier: 1.2 },
  { target: 'precipitation', bucket_name: 'Heavy (0.50+ in)',        bucket_low: 0.50, bucket_high: 5.0,  probability: 0.05, base_payout_multiplier: 11.0, jackpot_multiplier: 1.5 },
]

const FORECAST_DATES = [1, 2, 3, 4, 5].map(daysAhead)
const ALL_BUCKETS = [...HIGH_TEMP_BUCKETS, ...WIND_BUCKETS, ...PRECIP_BUCKETS]

export const MOCK_ODDS: OddsOption[] = FORECAST_DATES.flatMap((date, di) =>
  ALL_BUCKETS.map((b, bi) => ({
    ...b,
    id: di * ALL_BUCKETS.length + bi + 1,
    forecast_date: date,
  }))
)

// ── Leaderboard ────────────────────────────────────────────────────────────
export const MOCK_LEADERBOARD: LeaderboardResponse = {
  top: [
    { rank: 1,  username: 'WeatherWizard', credits_balance: 8_450 },
    { rank: 2,  username: 'MadisonMeteor', credits_balance: 6_230 },
    { rank: 3,  username: 'StormChaser99', credits_balance: 5_890 },
    { rank: 4,  username: 'BarometerBob',  credits_balance: 4_710 },
    { rank: 5,  username: 'FrontSystem',   credits_balance: 3_980 },
    { rank: 6,  username: 'dev_user',      credits_balance: 2_340 },
    { rank: 7,  username: 'ColdFront42',   credits_balance: 1_890 },
    { rank: 8,  username: 'WindVane',      credits_balance: 1_420 },
    { rank: 9,  username: 'IsobarIan',     credits_balance: 980  },
    { rank: 10, username: 'DewPoint',      credits_balance: 540  },
  ],
  current_user: { rank: 6, username: 'dev_user', credits_balance: 2_340 },
}

// ── Daily status ───────────────────────────────────────────────────────────
export const MOCK_DAILY_STATUS: DailyStatusResponse = { status: 'AVAILABLE' }

export const MOCK_DAILY_CLAIM: DailyClaimResponse = {
  message: 'Daily credits claimed!',
  added_credits: 100,
  new_balance: 2_440,
  status: 'CLAIMED',
}
