"use client";

import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAssistantContext } from "@/lib/assistant-context";

export function AskJaiosButton({ question }: { question: string }) {
  const { askAbout } = useAssistantContext();
  return (
    <Button variant="outline" size="sm" onClick={() => askAbout(question)}>
      <Sparkles className="mr-2 h-4 w-4" />
      Preguntar a JAIOS
    </Button>
  );
}
