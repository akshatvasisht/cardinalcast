import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/Table'
import { cn } from '@/lib/utils'
import type { LeaderboardEntry } from '@/api/types'

const RANK_CONFIG: Record<number, { row: string; rank: string }> = {
    1: { row: 'border-l-2 [border-left-color:color-mix(in_oklch,var(--medal-gold)_40%,transparent)]  [background-color:color-mix(in_oklch,var(--medal-gold)_10%,transparent)]',  rank: 'font-bold  [color:var(--medal-gold)]' },
    2: { row: 'border-l-2 [border-left-color:color-mix(in_oklch,var(--medal-silver)_40%,transparent)] [background-color:color-mix(in_oklch,var(--medal-silver)_10%,transparent)]', rank: 'font-semibold [color:var(--medal-silver)]' },
    3: { row: 'border-l-2 [border-left-color:color-mix(in_oklch,var(--medal-bronze)_40%,transparent)] [background-color:color-mix(in_oklch,var(--medal-bronze)_10%,transparent)]', rank: 'font-semibold [color:var(--medal-bronze)]' },
}

export function LeaderboardPage() {
    const { token } = useAuth()
    const [top, setTop] = useState<LeaderboardEntry[]>([])
    const [currentUser, setCurrentUser] = useState<LeaderboardEntry | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api
            .leaderboard(token)
            .then((data) => {
                setTop(data.top)
                setCurrentUser(data.current_user)
            })
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [token])

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
            <div className="page-header">
                <div>
                    <h2 className="page-title">Leaderboard</h2>
                    <p className="page-description">Top players by total credits.</p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Global Rankings</CardTitle>
                    <CardDescription>Updated in real-time based on resolved wagers.</CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <p className="text-muted-foreground text-center py-4">Loading...</p>
                    ) : top.length === 0 ? (
                        <p className="text-muted-foreground text-center py-4">No data available.</p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[100px]">Rank</TableHead>
                                    <TableHead>User</TableHead>
                                    <TableHead className="text-right">Credits</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {top.map((entry) => {
                                    const medal = RANK_CONFIG[entry.rank]
                                    const isYou = currentUser?.username === entry.username
                                    return (
                                        <TableRow key={entry.username} className={cn(medal?.row, !medal && isYou && 'bg-primary/5 border-l-2 border-l-primary/40')}>
                                            <TableCell className={cn('font-medium', medal?.rank, isYou && !medal && 'text-primary font-semibold')}>
                                                {entry.rank}
                                            </TableCell>
                                            <TableCell className={cn((medal || isYou) && 'font-medium')}>
                                                {entry.username}
                                                {isYou && <span className="ml-2 text-xs text-muted-foreground">(you)</span>}
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">{entry.credits_balance.toLocaleString()}</TableCell>
                                        </TableRow>
                                    )
                                })}
                                {currentUser && !top.some(e => e.username === currentUser.username) && (
                                    <>
                                        <TableRow>
                                            <TableCell colSpan={3} className="py-1 text-center">
                                                <span className="text-xs tracking-widest text-muted-foreground">- - -</span>
                                            </TableCell>
                                        </TableRow>
                                        <TableRow className="bg-primary/5 border-l-2 border-l-primary/40">
                                            <TableCell className="font-medium text-primary">
                                                {currentUser.rank}
                                            </TableCell>
                                            <TableCell className="font-medium">{currentUser.username} <span className="text-xs text-muted-foreground">(you)</span></TableCell>
                                            <TableCell className="text-right tabular-nums">{currentUser.credits_balance.toLocaleString()}</TableCell>
                                        </TableRow>
                                    </>
                                )}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
