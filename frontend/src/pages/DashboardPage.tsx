import { lazy, Suspense, useEffect, useState, useRef, useCallback, useMemo } from 'react'

import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import type { Wager } from '@/api/types'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { X } from 'lucide-react'
import { format, isBefore, startOfDay } from 'date-fns'
import { cn } from '@/lib/utils'
import { CalendarView } from '@/components/CalendarView'
import { DayDetailPanel } from '@/components/DayDetailPanel'
import { PlaceWagerDialog } from '@/components/PlaceWagerDialog'

const WeatherMap = lazy(() => import('@/components/WeatherMap').then(m => ({ default: m.WeatherMap })))

export function DashboardPage() {
  const { token, user } = useAuth()
  const [wagers, setWagers] = useState<Wager[]>([])

  // Calendar state
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined)
  const [displayedDate, setDisplayedDate] = useState<Date | undefined>(undefined)
  const [isExiting, setIsExiting] = useState(false)
  const [isWagerOpen, setIsWagerOpen] = useState(false)

  const wagerCardRef = useRef<HTMLDivElement>(null)
  const calendarContainerRef = useRef<HTMLDivElement>(null)
  const clearSelectedDate = useCallback(() => setSelectedDate(undefined), [])
  const noopPlaceWager = useCallback(() => { }, [])

  // Enter/exit animations for the date detail panel
  useEffect(() => {
    if (selectedDate) {
      setDisplayedDate(selectedDate)
      setIsExiting(false)
    } else if (displayedDate && !isExiting) {
      setIsExiting(true)
      const timer = setTimeout(() => {
        setDisplayedDate(undefined)
        setIsExiting(false)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [selectedDate, displayedDate, isExiting])

  // Close panel on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wagerCardRef.current?.contains(event.target as Node)) return
      if (calendarContainerRef.current?.contains(event.target as Node)) return
      setSelectedDate(undefined)
    }
    if (selectedDate) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [selectedDate])

  useEffect(() => {
    if (!token) return
    api.listWagers(token).then(setWagers).catch(() => { })
  }, [token])

  const selectedDateWagers = useMemo(() => {
    const targetDate = selectedDate || displayedDate
    if (!targetDate) return []
    const dateStr = format(targetDate, 'yyyy-MM-dd')
    return wagers.filter(w => w.forecast_date === dateStr)
  }, [wagers, selectedDate, displayedDate])

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4 overflow-hidden">
      <PlaceWagerDialog
        open={isWagerOpen}
        onOpenChange={setIsWagerOpen}
        initialDate={selectedDate || new Date()}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Wager Calendar</CardTitle>
            <CardDescription>Select a date to view placed wagers.</CardDescription>
          </CardHeader>
          <CardContent ref={calendarContainerRef} className="p-0">
            <CalendarView
              wagers={wagers}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
            />
          </CardContent>
        </Card>

        <Card className="flex flex-col overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle>Data Sources</CardTitle>
            <CardDescription>Live weather stations in Madison.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0 relative">
            <Suspense fallback={<div className="w-full h-full animate-pulse bg-muted/30 rounded" />}>
              <WeatherMap />
            </Suspense>
          </CardContent>
        </Card>
      </div>

      {displayedDate && (
        <Card
          ref={wagerCardRef}
          className={cn(
            "relative overflow-hidden border-primary/20 duration-500",
            isExiting
              ? "animate-out fade-out slide-out-to-bottom-4 fill-mode-forwards"
              : "animate-in fade-in slide-in-from-bottom-4"
          )}
        >
          <div className="p-0 border-b relative">
            <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent opacity-50" />
            <div className="relative z-10 px-5 py-2 flex items-center justify-between">
              <CardTitle className="text-base">{format(displayedDate, 'EEEE, MMMM do')}</CardTitle>
              <Button variant="ghost" size="icon" onClick={clearSelectedDate} aria-label="Close">
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <CardContent className="px-5 pt-3 pb-2">
            {isBefore(startOfDay(displayedDate), startOfDay(new Date())) ? (
              <div className="space-y-2">
                <h4 className="text-xs font-medium tracking-wide text-muted-foreground">Wagers</h4>
                <DayDetailPanel
                  date={displayedDate}
                  wagers={selectedDateWagers}
                  onClose={clearSelectedDate}
                  variant="embedded"
                  onPlaceWager={noopPlaceWager}
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <h4 className="text-xs font-medium tracking-wide text-muted-foreground">Existing Wagers</h4>
                  <DayDetailPanel
                    date={displayedDate}
                    wagers={selectedDateWagers}
                    onClose={clearSelectedDate}
                    variant="embedded"
                    onPlaceWager={noopPlaceWager}
                  />
                </div>
                <div className="space-y-2 lg:border-l lg:pl-5 pr-3">
                  <h4 className="text-xs font-medium tracking-wide text-muted-foreground">New Wager</h4>
                  <PlaceWagerDialog
                    open={true}
                    onOpenChange={() => { }}
                    initialDate={displayedDate}
                    hideTrigger={true}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
