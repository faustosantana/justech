"use client";

import { Suspense } from "react";
import {
  Calendar,
  Cloud,
  FileText,
  FolderOpen,
  Mail,
  MessageSquare,
  RefreshCw,
  Search,
  Settings,
  Shield,
  Share2,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  DEFAULT_M365_HEALTH,
  DEFAULT_M365_STATUS,
  M365_NOT_CONNECTED,
  M365_TABS,
  emptyM365ListResponse,
  emptyM365SearchResponse,
  type M365Health,
  type M365ListResponse,
  type M365SearchResponse,
  type M365Status,
  type M365TabId,
} from "@/lib/m365";
import { cn } from "@/lib/utils";

const TAB_ICONS: Record<M365TabId, typeof Mail> = {
  resumen: Cloud,
  outlook: Mail,
  sharepoint: Share2,
  onedrive: FolderOpen,
  calendario: Calendar,
  teams: Users,
  documentos: FileText,
  busqueda: Search,
  configuracion: Settings,
};

function isValidTab(value: string | null): value is M365TabId {
  return M365_TABS.some((t) => t.id === value);
}

export default function M365Page() {
  return (
    <Suspense
      fallback={
        <AppShell
          title="Centro de Inteligencia Microsoft 365"
          description="Correo, calendario, archivos y colaboración — contexto empresarial unificado"
        >
          <p className="text-sm text-muted-foreground">Cargando Centro de Inteligencia Microsoft 365…</p>
        </AppShell>
      }
    >
      <M365PageContent />
    </Suspense>
  );
}

function M365PageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab");
  const [tab, setTab] = useState<M365TabId>(
    isValidTab(initialTab) ? initialTab : "resumen",
  );
  const [health, setHealth] = useState<M365Health | null>(null);
  const [status, setStatus] = useState<M365Status | null>(null);
  const [tabData, setTabData] = useState<M365ListResponse | M365SearchResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const q = searchParams.get("tab");
    if (isValidTab(q) && q !== tab) setTab(q);
  }, [searchParams, tab]);

  const loadCore = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    let nextHealth: M365Health = DEFAULT_M365_HEALTH;
    let nextStatus: M365Status = DEFAULT_M365_STATUS;

    try {
      nextHealth = await apiClient.getM365Health();
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        router.replace("/login");
        return;
      }
      // API no alcanzable: mostrar estado informativo desconectado, no error rojo
    }

    try {
      nextStatus = await apiClient.getM365Status();
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        router.replace("/login");
        return;
      }
      // status opcional; health basta para el banner
      nextStatus = {
        ...DEFAULT_M365_STATUS,
        required_config: nextHealth.required_config,
        diagnostics: nextHealth.diagnostics ?? DEFAULT_M365_STATUS.diagnostics,
      };
    }

    if (!mountedRef.current) return;
    setHealth(nextHealth);
    setStatus(nextStatus);
    setLoading(false);
  }, [router]);

  const loadTabData = useCallback(async () => {
    if (!getAccessToken() || tab === "resumen" || tab === "configuracion") {
      setTabData(null);
      return;
    }
    setTabLoading(true);
    let data: M365ListResponse | M365SearchResponse =
      tab === "busqueda" ? emptyM365SearchResponse(searchQuery) : emptyM365ListResponse();
    try {
      switch (tab) {
        case "outlook":
          data = await apiClient.getM365OutlookMessages();
          break;
        case "sharepoint":
          data = await apiClient.getM365SharePointSites();
          break;
        case "onedrive":
          data = await apiClient.getM365OneDriveFiles();
          break;
        case "calendario":
          data = await apiClient.getM365CalendarEvents();
          break;
        case "teams":
          data = await apiClient.getM365Teams();
          break;
        case "documentos":
          data = await apiClient.getM365Documents();
          break;
        case "busqueda":
          data = await apiClient.getM365Search(searchQuery || " ");
          break;
        default:
          return;
      }
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        router.replace("/login");
        return;
      }
      // Pestaña sin conexión: estado informativo, sin banner de error
      data =
        tab === "busqueda"
          ? emptyM365SearchResponse(searchQuery)
          : emptyM365ListResponse();
    }
    if (mountedRef.current) setTabData(data);
    if (mountedRef.current) setTabLoading(false);
  }, [tab, searchQuery, router]);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    loadTabData();
  }, [loadTabData]);

  const handleTabChange = (id: M365TabId) => {
    setTab(id);
    router.replace(`/m365?tab=${id}`, { scroll: false });
  };

  const connected = health?.connected ?? false;
  const message = health?.message ?? M365_NOT_CONNECTED;
  const requiredConfig = status?.required_config ?? health?.required_config;

  return (
    <AppShell
      title="Centro de Inteligencia Microsoft 365"
      description="Correo, calendario, archivos y colaboración — contexto empresarial unificado"
    >
      <div className="space-y-6">
        <ConnectionBanner connected={connected} message={message} readOnly={health?.read_only ?? true} />

        <div className="flex flex-wrap items-center gap-2 border-b border-border pb-1">
          {M365_TABS.map(({ id, label }) => {
            const Icon = TAB_ICONS[id];
            return (
              <button
                key={id}
                type="button"
                onClick={() => handleTabChange(id)}
                className={cn(
                  "flex items-center gap-2 rounded-t-lg px-3 py-2 text-sm font-medium transition-colors",
                  tab === id
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={() => { setLoading(true); loadCore(); }} disabled={loading}>
              <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
              Actualizar
            </Button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando Centro de Inteligencia Microsoft 365…</p>
        ) : (
          <>
            {tab === "resumen" && status && (
              <ResumenTab status={status} health={health} />
            )}
            {tab === "configuracion" && requiredConfig && (
              <ConfiguracionTab status={status} requiredConfig={requiredConfig} />
            )}
            {tab !== "resumen" && tab !== "configuracion" && (
              <ResourceTab
                tab={tab}
                loading={tabLoading}
                data={tabData}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSearch={() => loadTabData()}
              />
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}

function ConnectionBanner({
  connected,
  message,
  readOnly,
}: {
  connected: boolean;
  message: string;
  readOnly: boolean;
}) {
  return (
    <Card className={cn("border-2", connected ? "border-success/30" : "border-warning/30")}>
      <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-xl",
              connected ? "bg-success/10 text-success" : "bg-warning/10 text-warning",
            )}
          >
            <Cloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-lg font-semibold">{message}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Integración Microsoft 365 no conectada. Configure las variables de entorno y OAuth cuando esté disponible.
            </p>
            {readOnly && (
              <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Shield className="h-3.5 w-3.5" />
                Modo solo lectura (M365_READ_ONLY=true)
              </p>
            )}
          </div>
        </div>
        <Button disabled title="OAuth pendiente — configure M365_CLIENT_ID y M365_TENANT_ID">
          Conectar Microsoft 365
        </Button>
      </CardContent>
    </Card>
  );
}

function ResumenTab({ status, health }: { status: M365Status; health: M365Health | null }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Próximos pasos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status.setup_steps.map((step) => (
            <div key={step.step} className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold">
                {step.step}
              </span>
              <div>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.description}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Permisos requeridos (lectura)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Delegados (usuario)
            </p>
            <div className="flex flex-wrap gap-1.5">
              {status.required_config.delegated_scopes.map((s) => (
                <span key={s} className="rounded-md bg-muted px-2 py-0.5 font-mono text-xs">
                  {s}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Aplicación (indexación futura)
            </p>
            <div className="flex flex-wrap gap-1.5">
              {status.required_config.application_scopes.map((s) => (
                <span key={s} className="rounded-md bg-muted px-2 py-0.5 font-mono text-xs">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {health?.diagnostics && (
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Diagnóstico</CardTitle>
          </CardHeader>
          <CardContent>
            <DiagnosticsPanel diagnostics={health.diagnostics} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ConfiguracionTab({
  status,
  requiredConfig,
}: {
  status: M365Status | null;
  requiredConfig: M365Status["required_config"];
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Variables de entorno</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {requiredConfig.config_keys.map((item) => (
            <div
              key={item.key}
              className="flex items-start justify-between gap-4 rounded-lg border border-border p-3"
            >
              <div>
                <p className="font-mono text-sm font-medium">{item.key}</p>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                  item.configured
                    ? "bg-success/10 text-success"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {item.configured ? "Definida" : "Pendiente"}
              </span>
            </div>
          ))}
          <p className="text-xs text-muted-foreground">
            Redirect URI: <code className="rounded bg-muted px-1">{requiredConfig.redirect_uri}</code>
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Arquitectura futura</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <FeatureFlag label="OAuth + refresh tokens" ready={requiredConfig.oauth_ready} />
          <FeatureFlag label="Microsoft Graph" ready={requiredConfig.graph_ready} />
          <FeatureFlag label="Multiusuario por tenant" ready={requiredConfig.multi_user_ready} />
          <FeatureFlag label="Indexación documental" ready={requiredConfig.indexing_ready} />
          <FeatureFlag label="Búsqueda empresarial" ready={requiredConfig.enterprise_search_ready} />
          <FeatureFlag label="Hermes Memory" ready={requiredConfig.hermes_memory_ready} />
          <FeatureFlag label="Qdrant" ready={requiredConfig.qdrant_ready} />
          <FeatureFlag label="JAIOS Assistant" ready={false} note="Stub activo — respuesta no conectado" />
        </CardContent>
      </Card>

      {status?.diagnostics && (
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Diagnóstico del módulo</CardTitle>
          </CardHeader>
          <CardContent>
            <DiagnosticsPanel diagnostics={status.diagnostics} />
          </CardContent>
        </Card>
      )}

      <Card className="lg:col-span-2 border-dashed">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <p className="font-medium">Conexión Microsoft 365</p>
            <p className="text-sm text-muted-foreground">
              La conexión OAuth se habilitará cuando el administrador complete la configuración en Azure AD.
            </p>
          </div>
          <Button disabled>Conectar Microsoft 365</Button>
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureFlag({
  label,
  ready,
  note,
}: {
  label: string;
  ready: boolean;
  note?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span>{label}</span>
      <span className={cn("text-xs", ready ? "text-success" : "text-muted-foreground")}>
        {ready ? "Listo" : note ?? "Pendiente"}
      </span>
    </div>
  );
}

function DiagnosticsPanel({
  diagnostics,
}: {
  diagnostics: NonNullable<M365Health["diagnostics"]>;
}) {
  const checks = [
    ["API alcanzable", diagnostics.api_reachable],
    ["Graph configurado (env)", diagnostics.graph_configured],
    ["OAuth implementado", diagnostics.oauth_implemented],
    ["Graph implementado", diagnostics.graph_implemented],
    ["Solo lectura activo", diagnostics.read_only_enforced],
    ["Auditoría activa", diagnostics.audit_enabled],
  ] as const;

  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2">
        {checks.map(([label, ok]) => (
          <div key={label} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
            <span>{label}</span>
            <span className={cn("font-medium", ok ? "text-success" : "text-warning")}>
              {ok ? "Sí" : "No"}
            </span>
          </div>
        ))}
      </div>
      {diagnostics.notes.length > 0 && (
        <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
          {diagnostics.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ResourceTab({
  tab,
  loading,
  data,
  searchQuery,
  onSearchChange,
  onSearch,
}: {
  tab: M365TabId;
  loading: boolean;
  data: M365ListResponse | M365SearchResponse | null;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  onSearch: () => void;
}) {
  const labels: Record<string, string> = {
    outlook: "correos",
    sharepoint: "sitios",
    onedrive: "archivos",
    calendario: "eventos",
    teams: "equipos",
    documentos: "documentos",
    busqueda: "resultados",
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle className="text-base capitalize">{tab}</CardTitle>
        {tab === "busqueda" && (
          <div className="flex gap-2">
            <input
              type="search"
              placeholder="Buscar en Microsoft 365…"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
            />
            <Button size="sm" variant="secondary" onClick={onSearch} disabled={loading}>
              <Search className="mr-1 h-4 w-4" />
              Buscar
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <DisconnectedState
            message={data?.message ?? M365_NOT_CONNECTED}
            resourceLabel={labels[tab] ?? "recursos"}
            total={data && "total" in data ? data.total : 0}
          />
        )}
      </CardContent>
    </Card>
  );
}

function DisconnectedState({
  message,
  resourceLabel,
  total,
}: {
  message: string;
  resourceLabel: string;
  total: number;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <MessageSquare className="h-10 w-10 text-muted-foreground/50" />
      <p className="text-lg font-medium">{message}</p>
      <p className="max-w-md text-sm text-muted-foreground">
        Cuando Microsoft 365 esté conectado, aquí verás {resourceLabel} en tiempo real desde Graph API.
        Actualmente: {total} registros.
      </p>
      <Button variant="outline" size="sm" disabled>
        Conectar Microsoft 365
      </Button>
    </div>
  );
}
