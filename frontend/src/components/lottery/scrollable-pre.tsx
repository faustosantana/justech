import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Scrollable JSON/pre block that remains keyboard-focusable (axe scrollable-region-focusable). */
export function ScrollablePre({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLPreElement>) {
  return (
    <pre
      tabIndex={0}
      className={cn("max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring", className)}
      {...rest}
    >
      {children}
    </pre>
  );
}
