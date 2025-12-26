import { useEffect, useState } from 'react'
import { useAuth, DEV_BYPASS_TOKEN } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import type { Wager } from '@/api/types'
import { TARGET_LABELS } from '@/api/types'
import { Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'

const STATUS_LABELS: Record<string, string> = {
  all: 'All',
  PENDING: 'Pending',
  PENDING_DATA: 'Awaiting Data',
  WIN: 'Win',
  LOSE: 'Lose',
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'

export function HistoryPage() {
  const { token } = useAuth()
  const [wagers, setWagers] = useState<Wager[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    if (!token) return
    if (token === DEV_BYPASS_TOKEN) {
      setLoading(false)
      return
    }
    api
      .listWagers(token)
      .then(setWagers)
      .finally(() => setLoading(false))
  }, [token])

  const filtered =
    filter === 'all' ? wagers : wagers.filter((w) => w.status === filter)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Wager history</h2>
          <p className="page-description">All your wagers and their status.</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Wagers</CardTitle>
            <CardDescription>Filter by status</CardDescription>
          </div>
          <div className="flex gap-2" role="group" aria-label="Filter wagers by status">
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
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Loading…</p>
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
                <Link to="/wagers/new">Place your first wager</Link>
              </Button>
            </div>
          ) : (
            <ul className="space-y-3">
              {filtered.map((w) => (
                <li
                  key={w.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-4"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {w.forecast_date ?? '—'} · {w.target ? TARGET_LABELS[w.target] ?? w.target : '—'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {w.wager_kind === 'OVER_UNDER' ? (
                        <>
                          {w.direction} {w.predicted_value}
                        </>
                      ) : (
                        <>
                          Bucket: {w.bucket_low ?? '—'} – {w.bucket_high ?? '—'}
                        </>
                      )}
                      {w.created_at && ` · Placed ${new Date(w.created_at).toLocaleString()}`}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{w.amount} credits</p>
                    <p
                      className={`text-sm font-medium ${w.status === 'WIN'
                        ? 'text-success'
                        : w.status === 'LOSE'
                          ? 'text-destructive'
                          : w.status === 'PENDING_DATA'
                            ? 'text-warning'
                            : 'text-muted-foreground'
                        }`}
                    >
                      {STATUS_LABELS[w.status] ?? w.status}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
