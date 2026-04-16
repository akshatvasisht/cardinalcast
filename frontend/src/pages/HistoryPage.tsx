import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import type { Wager } from '@/api/types'
import { TARGET_LABELS } from '@/api/types'
import { Plus, ChevronDown, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { format, parseISO, startOfWeek, isThisWeek, isSameWeek, subWeeks, startOfMonth } from 'date-fns'

// ── Status config ─────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  all: 'All',
  PENDING: 'Pending',
  PENDING_DATA: 'Awaiting Data',
  WIN: 'Win',
  LOSE: 'Lose',
}

const STATUS_BADGE: Record<string, string> = {
  WIN:          'bg-success/15 text-success border-success/30',
  LOSE:         'bg-destructive/15 text-destructive border-destructive/30',
  PENDING:      'bg-warning/15 text-warning border-warning/30',
  PENDING_DATA: 'bg-warning/15 text-warning border-warning/30',
}

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] ?? status
  const cls   = STATUS_BADGE[status] ?? 'bg-muted/50 text-muted-foreground border-border'
  return (
    <span className={`inline-flex items-center justify-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${cls}`}>
      {label}
    </span>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatReturn(w: Wager): { text: string; cls: string } {
  if (w.status === 'WIN' && w.winnings != null) {
    const net = w.winnings - w.amount
    return { text: `+${net}`, cls: 'text-success' }
  }
  if (w.status === 'LOSE') {
    return { text: `\u2212${w.amount}`, cls: 'text-destructive' }
  }
  return { text: '\u2014', cls: 'text-muted-foreground' }
}

type WeekGroup = { key: string; label: string; wagers: Wager[] }

function groupByPeriod(wagers: Wager[]): WeekGroup[] {
  const now = new Date()
  const groups = new Map<string, { label: string; sort: number; wagers: Wager[] }>()

  for (const w of wagers) {
    if (!w.forecast_date) continue
    const d = parseISO(w.forecast_date)

    let key: string
    let label: string
    let sort: number

    if (isThisWeek(d, { weekStartsOn: 0 })) {
      key = 'this-week'
      label = 'This Week'
      sort = startOfWeek(now, { weekStartsOn: 0 }).getTime()
    } else if (isSameWeek(d, subWeeks(now, 1), { weekStartsOn: 0 })) {
      key = 'last-week'
      label = 'Last Week'
      sort = startOfWeek(subWeeks(now, 1), { weekStartsOn: 0 }).getTime()
    } else {
      // Older than 2 weeks: group by calendar month
      const monthStart = startOfMonth(d)
      key = format(monthStart, 'yyyy-MM')
      label = format(monthStart, 'MMMM yyyy')
      sort = monthStart.getTime()
    }

    if (!groups.has(key)) {
      groups.set(key, { key, label, sort, wagers: [] })
    }
    groups.get(key)!.wagers.push(w)
  }

  return [...groups.values()]
    .sort((a, b) => b.sort - a.sort)
}

// ── Component ─────────────────────────────────────────────────────────────

export function HistoryPage() {
  const { token } = useAuth()
  const [wagers, setWagers] = useState<Wager[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!token) return
    api
      .listWagers(token)
      .then(setWagers)
      .catch(() => { })
      .finally(() => setLoading(false))
  }, [token])

  const filtered = filter === 'all' ? wagers : wagers.filter((w) => w.status === filter)
  const groups = useMemo(() => groupByPeriod(filtered), [filtered])

  // Auto-collapse older month groups; keep "this-week" and "last-week" open
  useEffect(() => {
    const initial = new Set(
      groups
        .filter(g => g.key !== 'this-week' && g.key !== 'last-week')
        .map(g => g.key)
    )
    setCollapsed(initial)
  }, [groups.map(g => g.key).join(',')])

  function toggleGroup(key: string) {
    setCollapsed(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const stats = useMemo(() => {
    const resolved = filtered.filter(w => w.status === 'WIN' || w.status === 'LOSE')
    const totalWagered = filtered.reduce((s, w) => s + w.amount, 0)
    const totalReturned = filtered.reduce((s, w) => s + (w.winnings ?? 0), 0)
    const wins = resolved.filter(w => w.status === 'WIN').length
    const winRate = resolved.length > 0 ? Math.round((wins / resolved.length) * 100) : null
    return { totalWagered, totalReturned, net: totalReturned - totalWagered, winRate, resolved: resolved.length }
  }, [filtered])

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      <div className="page-header">
        <h2 className="page-title">Wager History</h2>
        <div className="flex gap-1.5" role="group" aria-label="Filter wagers by status">
          {Object.keys(STATUS_LABELS).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilter(s)}
              aria-pressed={filter === s}
              aria-label={`Filter by ${STATUS_LABELS[s]}`}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${filter === s
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      <Card className="flex-1 min-h-0 flex flex-col">
        <CardContent className="p-0 flex-1 min-h-0 flex flex-col">
          {loading ? (
            <p className="text-muted-foreground px-6 py-6">Loading...</p>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <Plus className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold">No wagers found</h3>
              <p className="mb-6 text-sm text-muted-foreground">
                {filter === 'all' ? "You haven't placed any wagers yet." : `No ${(STATUS_LABELS[filter] || filter).toLowerCase()} wagers found.`}
              </p>
              <Button asChild>
                <Link to="/">Place your first wager</Link>
              </Button>
            </div>
          ) : (
            <div className="flex-1 min-h-0 flex flex-col">
            <div className="flex-1 min-h-0 overflow-y-auto">
              {groups.map((group) => {
                const isCollapsed = collapsed.has(group.key)
                return (
                <div key={group.key}>
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.key)}
                    className="sticky top-0 z-10 w-full bg-muted/40 backdrop-blur-sm border-b px-6 py-1.5 flex items-center gap-1.5 hover:bg-muted/60 transition-colors"
                  >
                    {isCollapsed
                      ? <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                      : <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
                    }
                    <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      {group.label}
                    </span>
                    {isCollapsed && (
                      <span className="ml-auto text-[11px] text-muted-foreground/60">
                        {group.wagers.length} wager{group.wagers.length !== 1 && 's'}
                      </span>
                    )}
                  </button>
                  {!isCollapsed && <ul className="divide-y divide-border">
                    {group.wagers.map((w) => {
                      const forecastLabel = w.forecast_date
                        ? format(parseISO(w.forecast_date), 'MMM d')
                        : '\u2014'
                      const betDetail = w.wager_kind === 'OVER_UNDER'
                        ? `${w.direction === 'OVER' ? 'Over' : 'Under'} ${w.predicted_value}`
                        : `${w.bucket_low ?? '\u2014'} \u2013 ${w.bucket_high ?? '\u2014'}`
                      const kindLabel = w.wager_kind === 'OVER_UNDER' ? 'O/U' : 'Bucket'
                      const ret = formatReturn(w)
                      return (
                        <li key={w.id} className="flex items-center gap-4 px-6 py-3.5">
                          {/* Date */}
                          <span className="w-14 shrink-0 text-sm tabular-nums text-muted-foreground">{forecastLabel}</span>

                          {/* Wager info */}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium">{w.target ? TARGET_LABELS[w.target] ?? w.target : '\u2014'}</span>
                              <span className="shrink-0 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground">
                                {kindLabel}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5">{betDetail}</p>
                          </div>

                          {/* Numeric columns */}
                          <span className="w-12 shrink-0 text-right text-sm tabular-nums text-muted-foreground">
                            {w.base_payout_multiplier != null ? `${w.base_payout_multiplier}x` : '\u2014'}
                          </span>
                          <span className="w-16 shrink-0 text-right text-sm tabular-nums font-medium">
                            {w.amount} cr
                          </span>
                          <span className={`w-16 shrink-0 text-right text-sm tabular-nums font-medium ${ret.cls}`}>
                            {ret.text}
                          </span>
                          <span className="w-[6.5rem] shrink-0 flex justify-end">
                            <StatusBadge status={w.status} />
                          </span>
                        </li>
                      )
                    })}
                  </ul>}
                </div>
                )
              })}

            </div>

            {/* Summary footer — outside scroll container so it stays visible */}
            {stats.resolved > 0 && (
              <div className="border-t bg-muted/30 px-6 py-3 flex items-center gap-4">
                <span className="flex-1 text-xs text-muted-foreground">
                  {stats.winRate}% win rate ({stats.resolved} resolved)
                </span>
                <span className="w-16 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                  {stats.totalWagered} cr
                </span>
                <span className={`w-16 shrink-0 text-right text-xs tabular-nums font-medium ${stats.net >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {stats.net >= 0 ? '+' : '\u2212'}{Math.abs(stats.net)}
                </span>
                <span className="w-24 shrink-0" />
              </div>
            )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
