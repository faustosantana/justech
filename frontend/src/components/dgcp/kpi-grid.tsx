import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  COMPANY_LABELS,
  formatCurrency,
  PRIORITY_LABELS,
  STATUS_LABELS,
  type DGCPSummary,
  type OpportunityCompany,
  type OpportunityPriority,
  type OpportunityStatus,
} from "@/lib/dgcp";

interface KPIGridProps {
  summary: DGCPSummary;
}

export function KPIGrid({ summary }: KPIGridProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Oportunidades</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold tabular-nums">
            {summary.total_opportunities}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Monto potencial</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold tabular-nums">
            {formatCurrency(summary.total_potential_amount)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Para licitar</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold tabular-nums text-success">
            {summary.to_bid}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Ganadas / Perdidas</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold tabular-nums">
            <span className="text-success">{summary.won}</span>
            <span className="text-muted-foreground mx-1">/</span>
            <span className="text-red-400">{summary.lost}</span>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <BreakdownCard title="Por empresa" items={summary.by_company} labelFn={(k) => COMPANY_LABELS[k as OpportunityCompany] ?? k} />
        <BreakdownCard title="Por prioridad" items={summary.by_priority} labelFn={(k) => PRIORITY_LABELS[k as OpportunityPriority] ?? k} />
        <BreakdownCard title="Por estado" items={summary.by_status} labelFn={(k) => STATUS_LABELS[k as OpportunityStatus] ?? k} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Estado de Presentación</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5 text-sm">
            <PresentationMetric label="Sin generar" value={summary.presentation?.sin_generar ?? 0} />
            <PresentationMetric label="Expediente generado" value={summary.presentation?.expediente_generado ?? 0} />
            <PresentationMetric label="Paquete DGCP" value={summary.presentation?.paquete_preparado ?? 0} />
            <PresentationMetric label="Listo para subir" value={summary.presentation?.listo_para_subir ?? 0} />
            <PresentationMetric label="Requiere actualización" value={summary.presentation?.requiere_actualizacion ?? 0} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Monto por empresa</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {Object.entries(summary.amount_by_company).map(([company, amount]) => (
              <div key={company} className="rounded-lg border border-border/50 p-3">
                <p className="text-xs text-muted-foreground">
                  {COMPANY_LABELS[company as OpportunityCompany] ?? company}
                </p>
                <p className="font-semibold tabular-nums">{formatCurrency(amount)}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PresentationMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function BreakdownCard({
  title,
  items,
  labelFn,
}: {
  title: string;
  items: Record<string, number>;
  labelFn: (key: string) => string;
}) {
  const entries = Object.entries(items).sort((a, b) => b[1] - a[1]);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin datos</p>
        ) : (
          entries.map(([key, count]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-muted-foreground">{labelFn(key)}</span>
              <span className="font-semibold tabular-nums">{count}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
