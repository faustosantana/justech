"use client";

import Link from "next/link";

import type { BusinessAnswerLink } from "@/lib/assistant-types";

interface AssistantLinksProps {
  links: BusinessAnswerLink[];
  onNavigate?: () => void;
}

export function AssistantLinks({ links, onNavigate }: AssistantLinksProps) {
  if (!links.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((lnk, i) =>
        lnk.url.startsWith("http") ? (
          <a
            key={i}
            href={lnk.url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-words text-xs text-primary hover:underline"
          >
            {lnk.label} ↗
          </a>
        ) : (
          <Link
            key={i}
            href={lnk.url}
            className="break-words text-xs text-primary hover:underline"
            onClick={onNavigate}
          >
            {lnk.label}
          </Link>
        ),
      )}
    </div>
  );
}
