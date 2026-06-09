"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/dgcp/status-badge";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  COMPANY_LABELS,
  formatCurrency,
  formatDate,
  PRIORITY_LABELS,
  priorityColor,
  scoreColor,
  type DGCPOpportunity,
} from "@/lib/dgcp";

interface OpportunitiesTableProps {
  items: DGCPOpportunity[];
  detailPath?: (id: string) => string;
}

export function OpportunitiesTable({
  items,
  detailPath = (id) => `/dgcp/${id}`,
}: OpportunitiesTableProps) {
  if (items.length === 0) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        No hay oportunidades. Ejecuta una sincronización con DGCP.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Código</TableHead>
          <TableHead>Empresa</TableHead>
          <TableHead className="min-w-[200px]">Título</TableHead>
          <TableHead className="text-right">Monto</TableHead>
          <TableHead className="text-center">Score</TableHead>
          <TableHead>Prioridad</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Fecha límite</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((opp) => (
          <TableRow key={opp.id} className="cursor-pointer">
            <TableCell>
              <Link
                href={detailPath(opp.id)}
                className="font-mono text-xs text-primary hover:underline"
              >
                {opp.code}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="muted" className="text-[10px]">
                {COMPANY_LABELS[opp.company]}
              </Badge>
              {opp.confidence_score > 0 && (
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {opp.confidence_score}% conf.
                </p>
              )}
            </TableCell>
            <TableCell>
              <Link href={detailPath(opp.id)} className="hover:text-primary line-clamp-2 text-sm">
                {opp.title}
              </Link>
              <p className="text-xs text-muted-foreground truncate max-w-[240px]">
                {opp.institution}
              </p>
            </TableCell>
            <TableCell className="text-right font-mono text-sm tabular-nums">
              {formatCurrency(opp.amount, opp.currency)}
            </TableCell>
            <TableCell className={`text-center font-semibold tabular-nums ${scoreColor(opp.score)}`}>
              {opp.score}
            </TableCell>
            <TableCell className={`text-sm ${priorityColor(opp.priority)}`}>
              {PRIORITY_LABELS[opp.priority]}
            </TableCell>
            <TableCell>
              <StatusBadge status={opp.status} />
            </TableCell>
            <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
              {formatDate(opp.deadline)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
