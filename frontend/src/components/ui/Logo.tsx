import React from 'react'
import { cn } from '@/lib/utils'

interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    className?: string
}

export function Logo({ className, ...props }: LogoProps) {
    return (
        <img
            src="/icon.png"
            alt="CardinalCast logo"
            className={cn('object-contain', className)}
            {...props}
        />
    )
}
