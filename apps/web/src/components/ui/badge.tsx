// From shadcn/ui (ui.shadcn.com), extended with three custom variants,
// success, warning, danger, for this app's status-badge system. Shadcn's
// own "destructive" variant is a bold solid-red fill, meant to stand out
// (an error count, say). This app's badges sit in soft-toned rows next to
// each other (SQL used, Grounded, Cached), so "danger" stays a soft red
// tint instead, matching success/warning's weight. The old app-specific
// "neutral" tone maps onto shadcn's own "secondary" variant, no custom
// variant needed there, it was already a close match.
//
// Same accent/muted swap as button.tsx: shadcn's outline/ghost hover into
// its own `accent` token, a subtle gray tint in its default theme. This
// app's `--accent` means the teal brand color, so those two hovers point
// at `muted` instead.
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
        destructive:
          "bg-destructive text-white focus-visible:ring-destructive/20 dark:bg-destructive/60 dark:focus-visible:ring-destructive/40 [a&]:hover:bg-destructive/90",
        outline: "border-border text-foreground [a&]:hover:bg-muted [a&]:hover:text-foreground",
        ghost: "[a&]:hover:bg-muted [a&]:hover:text-foreground",
        link: "text-primary underline-offset-4 [a&]:hover:underline",
        success: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
        warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
        danger: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span";

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };

