"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type DgcpUserMessage = {
  variant: "error" | "success" | "info";
  title: string;
  cause: string;
  nextStep: string;
};

type Props = {
  message: DgcpUserMessage;
  className?: string;
  onDismiss?: () => void;
};

export function DgcpUserMessageBanner({ message, className, onDismiss }: Props) {
  const isError = message.variant === "error";
  const isSuccess = message.variant === "success";

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 text-sm space-y-1",
        isError && "border-destructive/30 bg-destructive/5 text-destructive",
        isSuccess && "border-success/30 bg-success/5 text-success",
        !isError && !isSuccess && "border-primary/25 bg-primary/5",
        className,
      )}
      role={isError ? "alert" : "status"}
    >
      <div className="flex items-start gap-2">
        {isError ? (
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
        ) : isSuccess ? (
          <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
        ) : null}
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-medium text-foreground">{message.title}</p>
          <p className="text-foreground/90">{message.cause}</p>
          <p className="text-xs text-muted-foreground">{message.nextStep}</p>
        </div>
        {onDismiss ? (
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground shrink-0"
            onClick={onDismiss}
          >
            Cerrar
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function dgcpErrorFromUnknown(
  err: unknown,
  context: { title: string; fallbackCause: string; nextStep: string },
): DgcpUserMessage {
  let cause = context.fallbackCause;
  if (err instanceof Error && err.message && err.message !== "UNAUTHORIZED") {
    const msg = err.message.trim();
    if (msg && msg.toLowerCase() !== "error") cause = msg;
  }
  return {
    variant: "error",
    title: context.title,
    cause,
    nextStep: context.nextStep,
  };
}
