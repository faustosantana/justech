"use client";

import {
  DocumentsHubEmbed,
  EmpresasEmbed,
  ExecutiveReportEmbed,
  InteligenciaBandejaEmbed,
  PricesSearchEmbed,
  TasksListEmbed,
} from "./content-embeds";

export function PricesSearchSection() {
  return <PricesSearchEmbed />;
}

export function TasksSection({ sectionId }: { sectionId: string }) {
  return <TasksListEmbed sectionId={sectionId} />;
}

export function DocumentsHubSection() {
  return <DocumentsHubEmbed />;
}

export function EmpresasSection() {
  return <EmpresasEmbed />;
}

export function ExecutiveReportSection() {
  return <ExecutiveReportEmbed />;
}

export function InteligenciaBandejaSection() {
  return <InteligenciaBandejaEmbed />;
}
