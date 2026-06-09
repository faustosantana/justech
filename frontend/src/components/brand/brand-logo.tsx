import Image from "next/image";
import Link from "next/link";

import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";

type BrandLogoProps = {
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
  iconOnly?: boolean;
  href?: string;
  className?: string;
  inverted?: boolean;
};

const SIZES = {
  sm: { icon: 32, title: "text-base", sub: "text-[9px]" },
  md: { icon: 40, title: "text-lg", sub: "text-[10px]" },
  lg: { icon: 56, title: "text-2xl", sub: "text-xs" },
};

export function BrandLogo({
  size = "md",
  showSubtitle = true,
  iconOnly = false,
  href,
  className,
  inverted = false,
}: BrandLogoProps) {
  const s = SIZES[size];
  const content = (
    <span className={cn("inline-flex min-w-0 items-center gap-3", className)}>
      <Image
        src="/icons/jaios-512.svg"
        alt={BRAND.product}
        width={s.icon}
        height={s.icon}
        className={cn("shrink-0 rounded-xl shadow-sm", size === "lg" && "rounded-2xl shadow-lg shadow-black/15")}
        priority={size === "lg"}
      />
      {!iconOnly && (
        <span className="min-w-0 flex flex-col leading-none">
          {showSubtitle && (
            <span
              className={cn(
                "font-semibold uppercase tracking-[0.18em]",
                s.sub,
                inverted ? "text-blue-200/80" : "text-muted-foreground",
              )}
            >
              {BRAND.company} Group
            </span>
          )}
          <span className={cn("font-bold tracking-tight", s.title, inverted ? "text-white" : "text-foreground")}>
            {BRAND.product}
          </span>
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="inline-flex transition-opacity hover:opacity-90">
        {content}
      </Link>
    );
  }

  return content;
}
