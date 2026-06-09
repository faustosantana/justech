"use client";

interface AssistantWarningsProps {
  warnings: string[];
}

export function AssistantWarnings({ warnings }: AssistantWarningsProps) {
  if (!warnings.length) return null;
  return (
    <p className="break-words text-[10px] italic text-muted-foreground">{warnings.join(" ")}</p>
  );
}
