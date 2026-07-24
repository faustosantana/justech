"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { GroupEntry, TableKind } from "./motor-types";

type Props = {
  groups: Record<string, GroupEntry>;
  table: TableKind;
  title: string;
  highlightCode?: number;
};

export function MotorGroupsView({ groups, table, title, highlightCode }: Props) {
  const [qCode, setQCode] = useState(highlightCode != null ? String(highlightCode) : "");
  const [qMember, setQMember] = useState("");
  const detailBase =
    table === "table1"
      ? "/lottery/admin/control-center/motor/table1"
      : "/lottery/admin/control-center/motor/table2";

  const entries = useMemo(() => {
    let list = Object.values(groups || {}).sort((a, b) => a.code - b.code);
    const c = qCode.trim();
    const m = qMember.trim();
    if (c) list = list.filter((g) => String(g.code).includes(c));
    if (m) {
      const mn = Number(m);
      if (Number.isFinite(mn)) list = list.filter((g) => g.numbers.includes(mn));
      else list = list.filter((g) => g.numbers.some((n) => String(n).includes(m)));
    }
    return list;
  }, [groups, qCode, qMember]);

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Vista exclusiva de {table === "table1" ? "Tabla 1" : "Tabla 2"}. No mezcla la otra tabla.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Buscar código (ej. 34)"
            value={qCode}
            onChange={(e) => setQCode(e.target.value)}
            className="max-w-[200px]"
          />
          <Input
            placeholder="Buscar número integrante"
            value={qMember}
            onChange={(e) => setQMember(e.target.value)}
            className="max-w-[220px]"
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin grupos para el filtro actual.</p>
        ) : null}
        {entries.map((g) => (
          <div
            key={`${table}-${g.code}`}
            className={`rounded-md border p-3 ${highlightCode === g.code ? "border-primary" : ""}`}
          >
            <div className="font-semibold">
              Código {g.code} · {g.numbers.length} integrantes
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-sm">
              {g.numbers.map((n) => (
                <Link
                  key={n}
                  href={`${detailBase}?n=${n}`}
                  className="rounded border px-2 py-0.5 hover:bg-muted"
                >
                  {n}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
