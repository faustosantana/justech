"use client";

import { SpotlightSearch } from "@/components/search/spotlight-search";
import { useAppearance } from "@/lib/appearance-context";
import type { ExecutiveDashboard, ExecutiveKpi } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

import { HomeActivity } from "./home-activity";
import { HomeAppsGrid } from "./home-apps-grid";
import { HomeAssistantPanel } from "./home-assistant-panel";

type TodayStat = { label: string; value: string; href: string };

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}

function kpiValue(kpis: ExecutiveKpi[], id: string): string {
  return kpis.find((k) => k.id === id)?.value ?? "0";
}

function buildStats(kpis: ExecutiveKpi[], unreadConversations: number | null): TodayStat[] {
  return [
    {
      label: "conversaciones sin responder",
      value: unreadConversations !== null ? String(unreadConversations) : kpiValue(kpis, "critical_notifications"),
      href: "/comunicaciones",
    },
    {
      label: "oportunidades abiertas",
      value: kpiValue(kpis, "dgcp_bid"),
      href: "/dgcp",
    },
    {
      label: "licitaciones vigentes",
      value: kpiValue(kpis, "dgcp_active"),
      href: "/dgcp",
    },
    {
      label: "tareas pendientes",
      value: kpiValue(kpis, "my_pending"),
      href: "/tasks",
    },
  ];
}

type Props = {
  data: ExecutiveDashboard;
  unreadConversations: number | null;
};

export function PremiumHome({ data, unreadConversations }: Props) {
  const { settings } = useAppearance();
  const stats = buildStats(data.kpis, unreadConversations);
  const isCompact = settings.density === "compact";

  return (
    <div
      className={cn("home-backdrop relative min-h-[calc(100vh-3.5rem)] w-full", isCompact ? "home-density-compact" : "home-density-comfortable")}
      style={{ background: "var(--jaios-home-bg)" }}
    >
      <div className="mx-auto grid w-full max-w-[1600px] gap-6 lg:grid-cols-[1fr_300px] xl:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-8">
          <header className="space-y-5 pt-2">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl lg:text-4xl">
                {greeting()}, {data.user_name} <span className="inline-block animate-[wave_2s_ease-in-out_1]">👋</span>
              </h1>
              <p className="mt-2 text-sm text-muted-foreground md:text-base">
                Tu centro operativo · {data.company_name || data.tenant_name}
              </p>
            </div>

            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              {stats.map((s) => (
                <li key={s.label}>
                  <a href={s.href} className="group inline-flex items-baseline gap-1.5 transition hover:text-primary">
                    <span className="text-lg font-semibold tabular-nums text-foreground group-hover:text-primary">{s.value}</span>
                    <span className="text-muted-foreground">{s.label}</span>
                  </a>
                </li>
              ))}
            </ul>

            <SpotlightSearch />
          </header>

          <HomeAppsGrid compact={isCompact} />
          <HomeActivity items={data.activity} />
        </div>

        <div className="hidden lg:block">
          <div className="sticky top-6">
            <HomeAssistantPanel suggestions={data.assistant_suggestions} className="min-h-[420px]" />
          </div>
        </div>
      </div>

      <div className="mt-6 lg:hidden">
        <HomeAssistantPanel suggestions={data.assistant_suggestions} />
      </div>
    </div>
  );
}
