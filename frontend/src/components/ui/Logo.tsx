import React from 'react'
import { cn } from '@/lib/utils'

interface LogoProps extends React.SVGAttributes<SVGSVGElement> {
    className?: string
}

export function Logo({ className, ...props }: LogoProps) {
    return (
        <svg
            viewBox="0 0 40 40"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="CardinalCast logo"
            role="img"
            className={cn(className)}
            {...props}
        >
            <defs>
                <linearGradient id="logoGrad" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#D9040F" />
                    <stop offset="100%" stopColor="#8B0007" />
                </linearGradient>
            </defs>
            {/* Background rounded square */}
            <rect width="40" height="40" rx="9" fill="url(#logoGrad)" />
            {/* Left C — center (12, 20), radius 6.5, opens right */}
            <path
                d="M 16.6 15.4 A 6.5 6.5 0 1 0 16.6 24.6"
                stroke="white"
                strokeWidth="2.6"
                strokeLinecap="round"
                fill="none"
            />
            {/* Right C — center (26, 20), radius 6.5, opens right */}
            <path
                d="M 30.6 15.4 A 6.5 6.5 0 1 0 30.6 24.6"
                stroke="white"
                strokeWidth="2.6"
                strokeLinecap="round"
                fill="none"
            />
        </svg>
    )
}
