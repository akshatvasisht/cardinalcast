import { useEffect, useState, useRef } from 'react'

import { useAuth, DEV_BYPASS_TOKEN } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import type { Wager } from '@/api/types'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import { CalendarView } from '@/components/CalendarView'
import { DayDetailPanel } from '@/components/DayDetailPanel'
import { WeatherMap } from '@/components/WeatherMap'
import { PlaceWagerDialog } from '@/components/PlaceWagerDialog'

export function DashboardPage() {
  const { token, user, setUser } = useAuth()
  const [wagers, setWagers] = useState<Wager[]>([])
  const [dailyStatus, setDailyStatus] = useState<'AVAILABLE' | 'CLAIMED' | null>(null)
  const [claiming, setClaiming] = useState(false)
  const [claimMessage, setClaimMessage] = useState<string | null>(null)

  // Calendar State - defaulting to undefined to prevent auto-opening the dialog on load
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined)
  const [displayedDate, setDisplayedDate] = useState<Date | undefined>(undefined)
  const [isExiting, setIsExiting] = useState(false)
  const [isWagerOpen, setIsWagerOpen] = useState(false)

  const wagerCardRef = useRef<HTMLDivElement>(null)
  const calendarContainerRef = useRef<HTMLDivElement>(null)

  // Logic to handle enter/exit animations
  useEffect(() => {
    if (selectedDate) {
      setDisplayedDate(selectedDate)
      setIsExiting(false)
    } else if (displayedDate && !isExiting) {
      setIsExiting(true)
      const timer = setTimeout(() => {
        setDisplayedDate(undefined)
        setIsExiting(false)
      }, 500) // matches duration-500
      return () => clearTimeout(timer)
    }
  }, [selectedDate, displayedDate, isExiting])

  // Handle click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      // 1. If we clicked inside the wager card, it's NOT an "outside click"
      if (wagerCardRef.current && wagerCardRef.current.contains(event.target as Node)) {
        return;
      }

      // 2. If we clicked inside the calendar, it's NOT an "outside click" (keep it open for the new date)
      if (calendarContainerRef.current && calendarContainerRef.current.contains(event.target as Node)) {
        return;
      }

      // 3. Otherwise, it's an outside click - close the panel
      setSelectedDate(undefined);
    }

    if (selectedDate) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [selectedDate]);

  useEffect(() => {
    if (!token) return
    if (token === DEV_BYPASS_TOKEN) {
      return
    }
    // Fetch ALL wagers for the calendar
    api
      .listWagers(token)
      .then(setWagers)

    // Check daily credit claim status
    api
      .dailyStatus(token)
      .then((r) => setDailyStatus(r.status))
      .catch(() => {/* silently ignore */ })
  }, [token])

  async function handleClaim() {
    if (!token || token === DEV_BYPASS_TOKEN) return
    setClaiming(true)
    try {
      const result = await api.dailyClaim(token)
      setDailyStatus('CLAIMED')
      setClaimMessage(`+${result.added_credits} credits claimed!`)
      const updated = await api.me(token)
      setUser(updated)
    } catch (e) {
      setClaimMessage(e instanceof Error ? e.message : 'Claim failed')
    } finally {
      setClaiming(false)
    }
  }

  // Filter wagers for the selected date
  const selectedDateWagers = wagers.filter(w => {
    const targetDate = selectedDate || displayedDate
    if (!targetDate || !w.forecast_date) return false
    const dateStr = format(targetDate, 'yyyy-MM-dd')
    return w.forecast_date === dateStr
  })

  return (
    <div className="page-container">
      <PlaceWagerDialog
        open={isWagerOpen}
        onOpenChange={setIsWagerOpen}
        initialDate={selectedDate || new Date()}
      />
      <div className="page-header">
        <div>
          <h2 className="page-title">Dashboard</h2>
          <p className="page-description">
            Welcome, {user?.username}.
          </p>
        </div>
      </div>

      {/* Daily Claim Banner */}
      {dailyStatus === 'AVAILABLE' && !claimMessage && (
        <Card className="border-primary/40 bg-primary/5">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-base">🎁 Daily Credits Available</CardTitle>
            </div>
            <Button onClick={handleClaim} disabled={claiming} size="sm">
              {claiming ? 'Claiming…' : 'Claim 100 credits'}
            </Button>
          </CardHeader>
        </Card>
      )}
      {claimMessage && (
        <Card className="border-success/40 bg-success/5">
          <CardHeader className="py-3">
            <p className="text-sm font-medium text-success">✓ {claimMessage}</p>
          </CardHeader>
        </Card>
      )}

      {/* Main Content: Calendar + Map (Top Half) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Calendar - fixed height to always support up to 6 weeks */}
        <Card className="h-[500px] flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle>Wager Calendar</CardTitle>
            <CardDescription>Select a date to view placed wagers.</CardDescription>
          </CardHeader>
          <CardContent ref={calendarContainerRef} className="flex-1 overflow-hidden p-0">
            <CalendarView
              wagers={wagers}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
            />
          </CardContent>
        </Card>

        {/* Right: Map */}
        <Card className="h-full flex flex-col overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle>Data Sources</CardTitle>
            <CardDescription>Live weather stations in Madison.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 p-0 relative">
            <WeatherMap />
          </CardContent>
        </Card>
      </div>

      {displayedDate && (
        <Card
          ref={wagerCardRef}
          className={cn(
            "mt-4 relative overflow-hidden border-primary/20 duration-500",
            isExiting
              ? "animate-out fade-out slide-out-to-bottom-4 fill-mode-forwards"
              : "animate-in fade-in slide-in-from-bottom-4"
          )}
        >
          <div className="p-0 border-b relative">
            <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent opacity-50" />
            <div className="relative z-10 px-6 py-3 flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Wager Details & Placement</CardTitle>
                <CardDescription className="text-xs">View existing wagers and place a new one for {format(displayedDate, 'MMMM do, yyyy')}</CardDescription>
              </div>
            </div>
          </div>
          <CardContent className="p-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Existing Wagers</h4>
                <DayDetailPanel
                  date={displayedDate}
                  wagers={selectedDateWagers}
                  onClose={() => setSelectedDate(undefined)}
                  variant="embedded"
                  onPlaceWager={() => { }} // Internal transition no longer needed
                />
              </div>
              <div className="space-y-4 lg:border-l lg:pl-8">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">New Wager</h4>
                <PlaceWagerDialog
                  key={format(displayedDate, 'yyyy-MM-dd')} // Force form reset when date changes
                  open={true}
                  onOpenChange={() => { }} // embedded variant
                  initialDate={displayedDate}
                  hideTrigger={true}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  )
}
