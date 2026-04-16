import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/api/client'
import type { OddsOption } from '@/api/types'
import { TARGET_LABELS } from '@/api/types'
import { Button } from '@/components/ui/Button'
import { format } from 'date-fns'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/Dialog'
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/Form'
import { Input } from '@/components/ui/Input'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/Select'

const schema = z
    .object({
        forecast_date: z.string().min(1, 'Pick a date'),
        target: z.string().min(1, 'Pick a target'),
        amount: z.coerce.number().int().min(1, 'Amount must be at least 1'),
        wager_kind: z.enum(['BUCKET', 'OVER_UNDER']),
        bucket_id: z.string().optional(),
        direction: z.enum(['OVER', 'UNDER']).optional(),
        predicted_value: z.coerce.number().optional(),
    })
    .superRefine((data, ctx) => {
        if (data.wager_kind === 'BUCKET') {
            if (!data.bucket_id) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    message: 'Pick a bucket',
                    path: ['bucket_id'],
                })
            }
        } else {
            if (!data.direction) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    message: 'Pick a direction',
                    path: ['direction'],
                })
            }
            if (data.predicted_value === undefined || isNaN(data.predicted_value)) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    message: 'Enter a value',
                    path: ['predicted_value'],
                })
            }
        }
    })

type FormValues = z.infer<typeof schema>

interface PlaceWagerDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    initialDate?: Date
    hideTrigger?: boolean
}

export function PlaceWagerDialog({ open, onOpenChange, initialDate, hideTrigger }: PlaceWagerDialogProps) {
    const { token, user, setUser } = useAuth()
    const [odds, setOdds] = useState<OddsOption[]>([])
    const [loading, setLoading] = useState(true)
    const [submitError, setSubmitError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)
    const [estMultiplier, setEstMultiplier] = useState<number | null>(null)
    const [loadingMultiplier, setLoadingMultiplier] = useState(false)
    const closeTimerRef = useRef<ReturnType<typeof setTimeout>>(null)

    // Clean up close timer on unmount
    useEffect(() => {
        return () => { if (closeTimerRef.current) clearTimeout(closeTimerRef.current) }
    }, [])

    const form = useForm<FormValues>({
        resolver: zodResolver(schema) as Resolver<FormValues>,
        defaultValues: {
            forecast_date: '',
            target: '',
            amount: 10,
            wager_kind: 'BUCKET',
            bucket_id: '',
            direction: undefined,
            predicted_value: undefined,
        },
    })

    // Load odds once when dialog opens (not on every date change)
    useEffect(() => {
        if (open) {
            setLoading(true)
            setSuccess(false)
            setSubmitError(null)
            api.listOdds()
                .then(setOdds)
                .finally(() => setLoading(false))
        }
    }, [open])

    // When initialDate changes (or odds first load), reset form to the new date
    useEffect(() => {
        if (!odds.length || !initialDate) return
        const dateStr = format(initialDate, 'yyyy-MM-dd')
        const dateExists = odds.some(o => o.forecast_date === dateStr)
        form.reset({
            forecast_date: dateExists ? dateStr : '',
            target: '',
            amount: 10,
            wager_kind: 'BUCKET',
            bucket_id: '',
            direction: undefined,
            predicted_value: undefined,
        })
        setSuccess(false)
        setSubmitError(null)
    }, [initialDate, odds, form])

    const wagerKind = form.watch('wager_kind')
    const direction = form.watch('direction')
    const threshold = form.watch('predicted_value')
    const forecastDate = form.watch('forecast_date')
    const target = form.watch('target')

    // Calculate live multiplier estimate
    useEffect(() => {
        if (wagerKind !== 'OVER_UNDER' || !token || !forecastDate || !target || !direction || threshold === undefined) {
            setEstMultiplier(null)
            return
        }

        const timer = setTimeout(() => {
            setLoadingMultiplier(true)
            api.previewOverUnder(token, {
                forecast_date: forecastDate,
                target,
                direction,
                predicted_value: Number(threshold),
            })
                .then(res => setEstMultiplier(res.multiplier))
                .catch(() => setEstMultiplier(null))
                .finally(() => setLoadingMultiplier(false))
        }, 400)

        return () => clearTimeout(timer)
    }, [wagerKind, token, forecastDate, target, direction, threshold])

    const dates = useMemo(
        () => [...new Set(odds.map((o) => o.forecast_date))].sort(),
        [odds]
    )
    const targetsForDate = useMemo(
        () => forecastDate
            ? [...new Set(odds.filter((o) => o.forecast_date === forecastDate).map((o) => o.target))]
            : [],
        [odds, forecastDate]
    )
    const bucketsForDateTarget = useMemo(
        () => forecastDate && target
            ? odds.filter((o) => o.forecast_date === forecastDate && o.target === target)
            : [],
        [odds, forecastDate, target]
    )

    const onSubmit = useCallback(async (values: FormValues) => {
        if (!token) return
        setSubmitError(null)
        try {
            if (values.wager_kind === 'BUCKET') {
                const bucket = odds.find((o) => o.id === Number(values.bucket_id))
                if (!bucket) {
                    setSubmitError('Selected bucket not found')
                    return
                }
                const bucket_value = (bucket.bucket_low + bucket.bucket_high) / 2
                await api.placeWager(token, {
                    forecast_date: values.forecast_date,
                    target: values.target,
                    amount: values.amount,
                    wager_kind: 'BUCKET',
                    bucket_value,
                })
            } else {
                await api.placeWager(token, {
                    forecast_date: values.forecast_date,
                    target: values.target,
                    amount: values.amount,
                    wager_kind: 'OVER_UNDER',
                    direction: values.direction,
                    predicted_value: values.predicted_value,
                })
            }

            setSuccess(true)
            form.reset({
                forecast_date: '',
                target: '',
                amount: 10,
                wager_kind: 'BUCKET',
                bucket_id: '',
                direction: undefined,
                predicted_value: undefined,
            })

            const updated = await api.me(token)
            setUser(updated)

            // Close dialog after short delay
            closeTimerRef.current = setTimeout(() => {
                onOpenChange(false)
                setSuccess(false)
            }, 1500)

        } catch (e) {
            setSubmitError(e instanceof Error ? e.message : 'Failed to place wager')
        }
    }, [token, odds, onOpenChange, setUser])

    const content = (
        <>
            {!hideTrigger && (
                <DialogHeader>
                    <DialogTitle>Place a Wager</DialogTitle>
                    <DialogDescription>
                        Choose your forecast date, target, and wager details. Balance: <strong>{user?.credits_balance ?? 0}</strong> credits.
                    </DialogDescription>
                </DialogHeader>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-8">
                    <p className="text-muted-foreground">Loading market odds...</p>
                </div>
            ) : odds.length === 0 ? (
                <div className="py-4 text-center">
                    <p className="text-muted-foreground">No odds available yet.</p>
                </div>
            ) : (
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className={hideTrigger ? 'space-y-1.5' : 'space-y-3'}>
                        {submitError && (
                            <p className="text-sm font-medium text-destructive bg-destructive/10 p-2 rounded" role="alert" aria-live="assertive">{submitError}</p>
                        )}
                        {success && (
                            <p className="text-sm font-medium text-success bg-success/10 p-2 rounded" role="status" aria-live="polite">
                                Wager placed successfully! Closing...
                            </p>
                        )}

                        <div role="group" aria-label="Wager type" className="flex gap-2 p-1 bg-muted rounded-md">
                            <Button
                                type="button"
                                variant={wagerKind === 'BUCKET' ? 'secondary' : 'ghost'}
                                className="flex-1 h-7 text-xs"
                                aria-pressed={wagerKind === 'BUCKET'}
                                onClick={() => form.setValue('wager_kind', 'BUCKET')}
                            >
                                Bucket
                            </Button>
                            <Button
                                type="button"
                                variant={wagerKind === 'OVER_UNDER' ? 'secondary' : 'ghost'}
                                className="flex-1 h-7 text-xs"
                                aria-pressed={wagerKind === 'OVER_UNDER'}
                                onClick={() => form.setValue('wager_kind', 'OVER_UNDER')}
                            >
                                Over / Under
                            </Button>
                        </div>

                        <div className={hideTrigger ? '' : 'grid grid-cols-2 gap-3'}>
                            {!hideTrigger && (
                                <FormField
                                    control={form.control}
                                    name="forecast_date"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Forecast Date</FormLabel>
                                            <Select
                                                onValueChange={(v) => {
                                                    field.onChange(v)
                                                    form.setValue('target', '')
                                                    form.setValue('bucket_id', '')
                                                }}
                                                value={field.value}
                                            >
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select date" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {dates.map((d) => (
                                                        <SelectItem key={d} value={d}>
                                                            {d}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            )}

                            <FormField
                                control={form.control}
                                name="target"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className={hideTrigger ? 'sr-only' : undefined}>Target</FormLabel>
                                        <Select
                                            onValueChange={(v) => {
                                                field.onChange(v)
                                                form.setValue('bucket_id', '')
                                            }}
                                            value={field.value}
                                            disabled={!forecastDate}
                                        >
                                            <FormControl>
                                                <SelectTrigger className={hideTrigger ? 'h-8 text-sm' : ''}>
                                                    <SelectValue placeholder="Target" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {targetsForDate.map((t) => (
                                                    <SelectItem key={t} value={t}>
                                                        {TARGET_LABELS[t] ?? t}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        {wagerKind === 'BUCKET' ? (
                            <FormField
                                control={form.control}
                                name="bucket_id"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className={hideTrigger ? 'sr-only' : undefined}>Bucket</FormLabel>
                                        <Select
                                            onValueChange={field.onChange}
                                            value={field.value}
                                            disabled={!target}
                                        >
                                            <FormControl>
                                                <SelectTrigger className={hideTrigger ? 'h-8 text-sm' : ''}>
                                                    <SelectValue placeholder="Select bucket" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {bucketsForDateTarget.map((b) => (
                                                    <SelectItem key={b.id} value={String(b.id)}>
                                                        {b.bucket_name || `${b.bucket_low} – ${b.bucket_high}`} · {b.base_payout_multiplier}x
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        ) : (
                            <div className="grid grid-cols-2 gap-3">
                                <FormField
                                    control={form.control}
                                    name="direction"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className={hideTrigger ? 'sr-only' : undefined}>Direction</FormLabel>
                                            <div className="flex gap-1.5">
                                                <Button
                                                    type="button"
                                                    variant={field.value === 'OVER' ? 'default' : 'outline'}
                                                    className={hideTrigger ? 'flex-1 h-8 text-sm' : 'flex-1 h-9'}
                                                    onClick={() => field.onChange('OVER')}
                                                >
                                                    Over
                                                </Button>
                                                <Button
                                                    type="button"
                                                    variant={field.value === 'UNDER' ? 'default' : 'outline'}
                                                    className={hideTrigger ? 'flex-1 h-8 text-sm' : 'flex-1 h-9'}
                                                    onClick={() => field.onChange('UNDER')}
                                                >
                                                    Under
                                                </Button>
                                            </div>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="predicted_value"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className={hideTrigger ? 'sr-only' : undefined}>Threshold</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    step="0.1"
                                                    className={hideTrigger ? 'h-8 text-sm' : 'h-9'}
                                                    placeholder="e.g. 45.5"
                                                    {...field}
                                                    onChange={(e) => field.onChange(e.target.valueAsNumber)}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                            {(estMultiplier !== null || loadingMultiplier) && (
                                                <p className="text-xs font-medium text-primary text-right">
                                                    {loadingMultiplier ? 'Calculating...' : `Est. ${estMultiplier}x`}
                                                </p>
                                            )}
                                        </FormItem>
                                    )}
                                />
                            </div>
                        )}

                        <div className="flex items-end gap-3">
                            <FormField
                                control={form.control}
                                name="amount"
                                render={({ field }) => (
                                    <FormItem className="flex-1">
                                        <FormLabel className={hideTrigger ? 'sr-only' : undefined}>Amount (credits)</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                min={1}
                                                className={hideTrigger ? 'h-8 text-sm' : ''}
                                                {...field}
                                                onChange={(e) => field.onChange(e.target.valueAsNumber)}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <div className="flex gap-2 shrink-0 pb-[1px]">
                                {!hideTrigger && (
                                    <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                                        Cancel
                                    </Button>
                                )}
                                <Button type="submit" size={hideTrigger ? 'sm' : 'default'}>
                                    Place Wager
                                </Button>
                            </div>
                        </div>
                    </form>
                </Form>
            )}
        </>
    )

    if (hideTrigger) {
        return <div className="w-full">{content}</div>
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
                {content}
            </DialogContent>
        </Dialog>
    )
}
