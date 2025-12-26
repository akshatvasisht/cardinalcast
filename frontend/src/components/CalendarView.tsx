import { Calendar } from "@/components/ui/Calendar";
import { Wager, WagerStatus } from "@/api/types";
import { format } from "date-fns";

const CALENDAR_CLASSNAMES = {
    // Let the calendar fill the width of the card
    root: "w-full",
    // Tighten the caption area and make it relative for positioning context
    month_caption: "h-8 flex items-center justify-center relative",
    // Make nav absolutely span the caption area with visible arrows on sides
    nav: "absolute inset-0 flex items-center justify-between px-2 z-10",
    button_previous: "h-7 w-7 bg-transparent p-0 opacity-70 hover:opacity-100 rounded-md flex items-center justify-center m-0 hover:bg-accent transition-colors",
    button_next: "h-7 w-7 bg-transparent p-0 opacity-70 hover:opacity-100 rounded-md flex items-center justify-center m-0 hover:bg-accent transition-colors",
    // Override day to REMOVE aspect-square. This allows the calendar to stretch horizontally without stretching vertically.
    day: "relative h-12 w-full select-none p-0 text-center flex items-center justify-center",
    // Wager-specific selection highlight - centered circular background
    day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground !rounded-full h-10 w-10 flex items-center justify-center mx-auto",
};

const MODIFIER_CLASSNAMES = {
    hasWin: "text-success font-bold ring-2 ring-success/20 bg-success/10",
    hasLoss: "text-destructive font-bold ring-2 ring-destructive/20 bg-destructive/10",
    hasPending: "text-warning font-bold ring-2 ring-warning/20 bg-warning/10"
};

interface CalendarViewProps {
    wagers: Wager[];
    selectedDate: Date | undefined;
    onSelectDate: (date: Date | undefined) => void;
}

export function CalendarView({ wagers, selectedDate, onSelectDate }: CalendarViewProps) {
    // 1. Process wagers into a map of Date string -> Status[]
    const wagersByDate = wagers.reduce((acc, wager) => {
        if (!wager.forecast_date) return acc;
        // forecast_date is YYYY-MM-DD
        const dateStr = wager.forecast_date;
        if (!acc[dateStr]) {
            acc[dateStr] = [];
        }
        acc[dateStr].push(wager.status);
        return acc;
    }, {} as Record<string, string[]>);

    // 2. Modifiers for the calendar
    const modifiers = {
        hasWager: (date: Date) => {
            const dateStr = format(date, "yyyy-MM-dd");
            return !!wagersByDate[dateStr];
        },
        hasWin: (date: Date) => {
            const dateStr = format(date, "yyyy-MM-dd");
            return wagersByDate[dateStr]?.includes(WagerStatus.WIN) ?? false;
        },
        hasLoss: (date: Date) => {
            const dateStr = format(date, "yyyy-MM-dd");
            return wagersByDate[dateStr]?.includes(WagerStatus.LOSE) ?? false;
        },
        hasPending: (date: Date) => {
            const dateStr = format(date, "yyyy-MM-dd");
            const statuses = wagersByDate[dateStr] || [];
            return statuses.some(s => s === WagerStatus.PENDING || s === WagerStatus.PENDING_DATA);
        }
    };

    return (
        <div className="w-full h-full">
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
}
