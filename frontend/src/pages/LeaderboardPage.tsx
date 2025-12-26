import { useEffect, useState } from 'react'
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
import type { LeaderboardEntry } from '@/api/types'

export function LeaderboardPage() {
    const [entries, setEntries] = useState<LeaderboardEntry[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api
            .leaderboard()
            .then(setEntries)
            .finally(() => setLoading(false))
    }, [])

    return (
        <div className="page-container">
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
                    ) : entries.length === 0 ? (
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
                                {entries.map((entry) => (
                                    <TableRow key={entry.username}>
                                        <TableCell className="font-medium">{entry.rank}</TableCell>
                                        <TableCell>{entry.username}</TableCell>
                                        <TableCell className="text-right">{entry.credits_balance.toLocaleString()}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
