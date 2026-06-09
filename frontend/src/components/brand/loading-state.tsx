import { BrandLogo } from "@/components/brand/brand-logo";
import { cn } from "@/lib/utils";

type LoadingStateProps = {
  message?: string;
  fullScreen?: boolean;
  className?: string;
};

export function LoadingState({
  message = "Cargando…",
  fullScreen = true,
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-5",
        fullScreen && "min-h-screen platform-backdrop",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className="relative">
        <div className="absolute inset-0 animate-ping rounded-2xl bg-primary/20" />
        <BrandLogo size="md" showSubtitle={false} className="relative animate-pulse" />
      </div>
      <p className="text-sm font-medium text-muted-foreground">{message}</p>
    </div>
  );
}
