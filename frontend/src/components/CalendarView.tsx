import { memo, useMemo } from "react";
import { Calendar } from "@/components/ui/Calendar";
import { Wager, WagerStatus } from "@/api/types";
import { format } from "date-fns";

const CALENDAR_CLASSNAMES = {
    // Let the calendar fill the width of the card
    root: "w-full",
    // month is the positioning context for the absolutely-placed nav
    month: "flex w-full flex-col gap-4 relative",
    // Caption is centered; nav overlays it via absolute positioning on month
    month_caption: "h-10 flex items-center justify-center",
    // nav is absolute relative to month, overlaying just the caption row
    nav: "absolute top-0 inset-x-0 h-10 flex items-center justify-between px-1 z-10",
    button_previous: "h-7 w-7 bg-transparent p-0 opacity-70 hover:opacity-100 rounded-md flex items-center justify-center hover:bg-primary/10 transition-colors",
    button_next: "h-7 w-7 bg-transparent p-0 opacity-70 hover:opacity-100 rounded-md flex items-center justify-center hover:bg-primary/10 transition-colors",
    // TD: fixed height, full width, centers the button inside.
    // Button forced to size-10 (40px) to fill the 48px cell without crowding.
    // Hover override: bg-accent is invisible in dark mode, use primary/10 instead.
    day: "relative h-12 w-full select-none text-center flex items-center justify-center [&_button]:size-10 [&_button:not([data-selected-single=true]):hover]:!bg-primary/10",
    // Today: ring on the TD behind the button — but since button is now fixed size (--cell-size),
    // we target the button directly so ring and selected-bg are on the same element at the same size.
    today: "[&_button]:ring-2 [&_button]:ring-foreground/30 [&_button]:rounded-md",
};

const MODIFIER_CLASSNAMES = {
    hasWin: "[&_button]:ring-2 [&_button]:ring-success/40 [&_button]:bg-success/15 [&_button]:text-success [&_button]:font-bold [&_button]:rounded-md",
    hasLoss: "[&_button]:ring-2 [&_button]:ring-destructive/40 [&_button]:bg-destructive/15 [&_button]:text-destructive [&_button]:font-bold [&_button]:rounded-md",
    hasPending: "[&_button]:ring-2 [&_button]:ring-warning/40 [&_button]:bg-warning/15 [&_button]:text-warning [&_button]:font-bold [&_button]:rounded-md",
};

interface CalendarViewProps {
    wagers: Wager[];
    selectedDate: Date | undefined;
    onSelectDate: (date: Date | undefined) => void;
}

export const CalendarView = memo(function CalendarView({ wagers, selectedDate, onSelectDate }: CalendarViewProps) {
    // 1. Process wagers into a map of Date string -> Status[] — memoized so it only
    //    recomputes when the wager list actually changes, not on every render.
    const wagersByDate = useMemo(() => {
        return wagers.reduce((acc, wager) => {
            if (!wager.forecast_date) return acc;
            const dateStr = wager.forecast_date;
            if (!acc[dateStr]) acc[dateStr] = [];
            acc[dateStr].push(wager.status);
            return acc;
        }, {} as Record<string, string[]>);
    }, [wagers]);

    // 2. Modifiers — memoized so the calendar does not re-register functions on every render.
    const modifiers = useMemo(() => ({
        hasWager: (date: Date) => !!wagersByDate[format(date, "yyyy-MM-dd")],
        hasWin: (date: Date) => wagersByDate[format(date, "yyyy-MM-dd")]?.includes(WagerStatus.WIN) ?? false,
        hasLoss: (date: Date) => wagersByDate[format(date, "yyyy-MM-dd")]?.includes(WagerStatus.LOSE) ?? false,
        hasPending: (date: Date) => {
            const statuses = wagersByDate[format(date, "yyyy-MM-dd")] || [];
            return statuses.some(s => s === WagerStatus.PENDING || s === WagerStatus.PENDING_DATA);
        },
    }), [wagersByDate]);

    return (
        <div className="w-full" aria-label="Wager calendar" role="region">
            <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={onSelectDate}
                className="w-full pt-1 px-4 pb-4"
                classNames={CALENDAR_CLASSNAMES}
                modifiers={modifiers}
                modifiersClassNames={MODIFIER_CLASSNAMES}
            />
        </div>
    );
})
