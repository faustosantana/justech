'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import { canAccessLotteryModule, DISCLAIMER } from '@/lib/lottery'

type Dash = {
  motor?: Record<string, unknown>
  resultados?: Record<string, unknown>
  piloto?: Record<string, unknown>
  rendimiento?: Record<string, unknown>
  ultimo_sorteo?: Record<string, unknown>
  freeze?: Record<string, unknown>
}

function pct(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(1)}%`
}

export default function LotteryIaDashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<Dash | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError('Sin permiso')
      return
    }
    try {
      setData((await apiClient.getLotteryIaDashboard()) as Dash)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el Dashboard')
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const m = data?.motor || {}
  const r = data?.resultados || {}
  const p = data?.piloto || {}
  const perf = data?.rendimiento || {}
  const last = data?.ultimo_sorteo || {}
  const resultado = (last.resultado || {}) as Record<string, unknown>

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Lottery IA</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Panel de estado — solo lectura. Motor v1.0 congelado. {DISCLAIMER}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void load()}>
              Actualizar
            </Button>
            <Button variant="outline" asChild>
              <Link href="/lottery/resultados">Resultados</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/lottery/prospective-pilot">Piloto</Link>
            </Button>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-base">
                Motor
                <Badge variant="success">{String(m.estado ?? '—')}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row k="Versión" v={`v${String(m.version ?? '—')}`} />
              <Row k="Perfil activo" v={String(m.perfil_activo ?? '—')} />
              <Row k="Tiebreak" v={String((data?.freeze as Record<string, unknown> | undefined)?.tiebreak ?? m.tiebreak_activo ?? '—')} />
              <Row k="Política" v={String((data?.freeze as Record<string, unknown> | undefined)?.tiebreak_policy ?? 'EMPATE_MULTI_FUERTE')} />
              <Row k="Estado congelado" v={String(m.estado ?? '—')} />
              <Row k="Fecha freeze" v={String(m.fecha_congelamiento ?? '—')} />
              <Row k="Commit" v={String(m.commit ?? '—')} />
              <Row k="Tag" v={String((data?.freeze as Record<string, unknown> | undefined)?.release_tag ?? 'lottery-ia-motor-v1.0')} />
              <p className="pt-2 text-xs text-muted-foreground">Solo lectura — no editable en UI.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Resultados</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row k="Última actualización" v={String(r.ultima_actualizacion ?? '—')} />
              <Row k="Total sorteos" v={String(r.total_sorteos ?? '—')} />
              <Row k="Total loterías" v={String(r.total_loterias ?? '—')} />
              <Row k="Pendientes sync" v={String(r.pendientes_sincronizar ?? '—')} />
              <Row k="Estado sync" v={String(r.estado_sync ?? '—')} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Piloto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row k="LOCKED" v={String(p.locked ?? '—')} />
              <Row k="Evaluadas" v={String(p.evaluadas ?? '—')} />
              <Row k="Pendientes" v={String(p.pendientes ?? '—')} />
              <Row k="Draft" v={String(p.draft ?? '—')} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Rendimiento</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row k="Top 1 (∨ multi)" v={pct(perf.top1)} />
              <Row k="Top 2" v={pct(perf.top2)} />
              <Row k="Multi-Fuerte" v={pct(perf.multi_fuerte)} />
              <p className="pt-2 text-xs text-muted-foreground">{String(perf.label ?? '')}</p>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-base">
                Último sorteo
                <Badge
                  variant={
                    last.estado === 'Correcto'
                      ? 'success'
                      : last.estado === 'Incorrecto'
                        ? 'danger'
                        : 'muted'
                  }
                >
                  {String(last.estado ?? '—')}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row k="Lotería" v={String(last.loteria ?? '—')} />
              <Row k="Fecha" v={String(last.fecha ?? '—')} />
              <Row
                k="Resultado"
                v={
                  resultado.primera
                    ? `${resultado.primera} · ${resultado.segunda ?? '—'} · ${resultado.tercera ?? '—'}`
                    : '—'
                }
              />
              <Row
                k="Predicción"
                v={
                  Array.isArray(last.prediccion)
                    ? (last.prediccion as unknown[]).join(', ')
                    : String(last.prediccion ?? '—')
                }
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/40 py-1 last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="text-right font-medium break-all">{v}</span>
    </div>
  )
}
