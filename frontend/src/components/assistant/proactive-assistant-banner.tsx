"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AssistantAvatar, type AssistantAvatarState } from "@/components/assistant/assistant-avatar";
import { Button } from "@/components/ui/button";
import { useAssistantContext } from "@/lib/assistant-context";
import { getProactivePrompt, type ProactiveAction } from "@/lib/assistant-proactive";
import { cn } from "@/lib/utils";

interface ProactiveAssistantBannerProps {
  className?: string;
  overrideMessage?: string;
}

export function ProactiveAssistantBanner({
  className,
  overrideMessage,
}: ProactiveAssistantBannerProps) {
  const pathname = usePathname();
  const { askAbout } = useAssistantContext();
  const prompt = getProactivePrompt(pathname);
  const message = overrideMessage || prompt.message;

  function runAction(action: ProactiveAction) {
    if (action.question) {
      askAbout(action.question);
      return;
    }
    if (action.href) {
      window.location.href = action.href;
    }
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-2xl border border-primary/20 bg-gradient-to-r from-primary/10 via-background to-background p-4 shadow-sm md:flex-row md:items-center",
        className,
      )}
    >
      <AssistantAvatar size="md" state={prompt.state as AssistantAvatarState} animated />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-primary">Assistant proactivo</p>
        <p className="mt-1 text-sm leading-relaxed text-foreground">{message}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {prompt.actions.map((action) =>
            action.href && !action.question ? (
              <Button key={action.label} variant="outline" size="sm" asChild>
                <Link href={action.href}>{action.label}</Link>
              </Button>
            ) : (
              <Button
                key={action.label}
                variant="outline"
                size="sm"
                onClick={() => runAction(action)}
              >
                {action.label}
              </Button>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
