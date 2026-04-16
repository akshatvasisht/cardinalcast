import { memo } from "react";
import { format } from "date-fns";
import { Wager, TARGET_LABELS } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { X } from "lucide-react";

interface DayDetailPanelProps {
    date: Date | undefined;
    wagers: Wager[];
    onClose: () => void;
    variant?: "card" | "embedded";
    onPlaceWager?: () => void;
}

export const DayDetailPanel = memo(function DayDetailPanel({ date, wagers, onClose, variant = "card", onPlaceWager }: DayDetailPanelProps) {
    if (!date) return null;

    const content = (
        <div className="space-y-4">
            {wagers.length > 0 ? (
                <ul className="space-y-3">
                    {wagers.map((w) => (
                        <li key={w.id} className="p-3 text-sm border rounded-md bg-muted/50">
                            <div className="flex justify-between mb-1 font-medium">
                                <span>{w.target ? TARGET_LABELS[w.target] : "Unknown"}</span>
                                <span className={
                                    w.status === 'WIN' ? 'text-success' :
                                        w.status === 'LOSE' ? 'text-destructive' :
                                            'text-warning'
                                }>{w.status}</span>
                            </div>
                            <div className="flex justify-between text-muted-foreground">
                                <span>
                                    {w.wager_kind === 'OVER_UNDER'
                                        ? `${w.direction} ${w.predicted_value}`
                                        : `[${w.bucket_low} - ${w.bucket_high}]`
                                    }
                                </span>
                                <span>{w.amount} credits</span>
                            </div>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="text-sm text-muted-foreground">No wagers placed for this date.</p>
            )}

            {variant !== "embedded" && (
                <div className="pt-4">
                    <Button onClick={onPlaceWager} className="w-full">
                        Place Wager
                    </Button>
                </div>
            )}
        </div>
    );

    if (variant === "embedded") {
        return (
            <div className="flex-1 flex flex-col">
                {wagers.length > 0 ? (
                    <ul className="space-y-3">
                        {wagers.map((w) => (
                            <li key={w.id} className="p-3 text-sm border rounded-md bg-muted/50">
                                <div className="flex justify-between mb-1 font-medium">
                                    <span>{w.target ? TARGET_LABELS[w.target] : "Unknown"}</span>
                                    <span className={
                                        w.status === 'WIN' ? 'text-success' :
                                            w.status === 'LOSE' ? 'text-destructive' :
                                                'text-warning'
                                    }>{w.status}</span>
                                </div>
                                <div className="flex justify-between text-muted-foreground">
                                    <span>
                                        {w.wager_kind === 'OVER_UNDER'
                                            ? `${w.direction} ${w.predicted_value}`
                                            : `[${w.bucket_low} - ${w.bucket_high}]`
                                        }
                                    </span>
                                    <span>{w.amount} credits</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <div className="flex-1 flex items-center justify-center">
                        <p className="text-sm text-muted-foreground text-center">No wagers for this date.</p>
                    </div>
                )}
            </div>
        );
    }

    return (
        <Card className="h-full border rounded-md shadow-none">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <div className="space-y-1">
                    <CardTitle>{format(date, "EEEE, MMMM do")}</CardTitle>
                    <CardDescription>
                        {wagers.length} wager{wagers.length !== 1 && "s"} for this day
                    </CardDescription>
                </div>
                <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close wager details">
                    <X className="w-4 h-4" />
                </Button>
            </CardHeader>
            <CardContent>
                {content}
            </CardContent>
        </Card>
    );
})
