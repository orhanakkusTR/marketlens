/**
 * shadcn pattern Button — Binance dark renkleriyle.
 * (Radix Slot bağımlılığı yok; asChild Adım 21+'da eklenebilir.)
 */
import * as React from "react";
import { type VariantProps, cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-binance-accent/60 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-binance-accent text-binance-bg hover:bg-binance-accent/90",
        secondary:
          "bg-binance-surface text-binance-text-primary border border-binance-border hover:bg-binance-border/40",
        outline:
          "border border-binance-border text-binance-text-primary hover:bg-binance-surface",
        ghost:
          "text-binance-text-secondary hover:bg-binance-surface hover:text-binance-text-primary",
        destructive:
          "bg-binance-short text-white hover:bg-binance-short/90",
        link: "text-binance-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
