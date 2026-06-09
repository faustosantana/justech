import { cn } from "@/lib/utils";

export type AssistantAvatarState = "normal" | "thinking" | "alert" | "success" | "attention";

interface AssistantAvatarProps {
  state?: AssistantAvatarState;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  animated?: boolean;
}

const sizeMap = {
  sm: "h-10 w-10",
  md: "h-14 w-14",
  lg: "h-20 w-20",
  xl: "h-28 w-28",
};

export function AssistantAvatar({
  state = "normal",
  size = "md",
  className,
  animated = false,
}: AssistantAvatarProps) {
  const ring =
    state === "thinking"
      ? "ring-2 ring-primary/40 animate-pulse"
      : state === "alert"
        ? "ring-2 ring-warning/60"
        : state === "success"
          ? "ring-2 ring-success/50"
          : state === "attention"
            ? "ring-2 ring-destructive/50 animate-pulse"
            : "ring-1 ring-primary/20";

  return (
    <div
      className={cn(
        "relative shrink-0 rounded-2xl bg-gradient-to-br from-primary to-secondary p-[2px] shadow-lg",
        sizeMap[size],
        ring,
        animated && state === "normal" && "animate-[pulse_3s_ease-in-out_infinite]",
        className,
      )}
      aria-hidden
    >
      <svg viewBox="0 0 120 120" className="h-full w-full rounded-[14px] bg-white">
        <defs>
          <linearGradient id="jaios-head" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(222 47% 16%)" />
            <stop offset="100%" stopColor="hsl(217 91% 45%)" />
          </linearGradient>
        </defs>
        <rect width="120" height="120" rx="18" fill="hsl(210 40% 98%)" />
        <circle cx="60" cy="52" r="30" fill="url(#jaios-head)" />
        <rect x="34" y="78" width="52" height="24" rx="12" fill="hsl(222 47% 16%)" />
        <circle cx="48" cy="50" r="6" fill="#ecfdf5" />
        <circle cx="72" cy="50" r="6" fill="#ecfdf5" />
        <circle
          cx="48"
          cy="50"
          r="3"
          fill="hsl(142 76% 36%)"
          className={cn(state === "thinking" && animated && "animate-pulse")}
        />
        <circle
          cx="72"
          cy="50"
          r="3"
          fill="hsl(142 76% 36%)"
          className={cn(state === "thinking" && animated && "animate-pulse")}
        />
        <path
          d="M48 62 Q60 70 72 62"
          stroke="hsl(217 91% 75%)"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
        />
        <rect x="52" y="18" width="16" height="8" rx="4" fill="hsl(217 91% 45%)" />
        <circle
          cx="60"
          cy="14"
          r="4"
          fill="hsl(142 76% 36%)"
          className={cn(animated && "animate-ping opacity-75")}
        />
      </svg>
      {state === "thinking" && (
        <span className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] text-white">
          …
        </span>
      )}
      {state === "alert" && (
        <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-warning" />
      )}
    </div>
  );
}
