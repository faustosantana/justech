'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { LotteryNumberLink } from '@/components/lottery/lottery-number-link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import { canAccessLotteryModule, DISCLAIMER } from '@/lib/lottery'

type Analysis = {
  primary_signal?: { number?: number; reason?: string; classification?: string } | null
  alternatives?: { number: number; classification?: string; score?: number }[]
  multi_strong_candidates?: number[]
  ranked_candidates?: { number: number; classification?: string }[]
  explanation?: { summary?: string }
  observed_numbers?: number[]
  graph?: { nodes?: { id?: string; number?: number; role?: string }[] }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

export default function LotteryAnalizarPage() {
  const router = useRouter()
  const search = useSearchParams()
  const [number, setNumber] = useState(search.get('number') || '')
  const [companion, setCompanion] = useState(search.get('with') || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Analysis | null>(null)

  const run = useCallback(
    async (nRaw?: string, withRaw?: string) => {
      const n = Number(String(nRaw ?? number).replace(/\D/g, ''))
      const w = String(withRaw ?? companion).replace(/\D/g, '')
      if (!Number.isInteger(n) || n < 1 || n > 100) {
        setError('Indique un número entre 1 y 100.')
        return
      }
      const token = getAccessToken()
      if (!token) {
        router.replace('/login?session=expired')
        return
      }
      if (!canAccessLotteryModule(getUserRole())) {
        setError('Sin permiso para Lottery IA.')
        return
      }
      const numbers = w ? [n, Number(w)] : [n]
      if (w && (!Number.isInteger(Number(w)) || Number(w) < 1 || Number(w) > 100)) {
        setError('El segundo número debe estar entre 1 y 100.')
        return
      }
      setBusy(true)
      setError(null)
      try {
        const res = await fetch(`${API_BASE}/analysis/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            numbers,
            mode: 'socio',
            derivation_depth: 0,
            create_signals: false,
            explanation_level: 'analitico',
          }),
        })
        if (!res.ok) {
          let detail = 'No fue posible completar el análisis. Intente nuevamente.'
          try {
            const body = await res.json()
            if (typeof body?.detail === 'string' && body.detail.length < 180) detail = body.detail
          } catch {
            /* ignore */
          }
          throw new ApiError(res.status, 'ANALYZE_FAILED', detail)
        }
        setData((await res.json()) as Analysis)
      } catch (err) {
        setData(null)
        setError(
          err instanceof ApiError
            ? err.message
            : 'No fue posible consultar el análisis. Intente nuevamente.',
        )
      } finally {
        setBusy(false)
      }
    },
    [number, companion, router],
  )

  useEffect(() => {
    if (search.get('auto') === '1' && search.get('number')) {
      void run(search.get('number') || undefined, search.get('with') || undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const primary = data?.primary_signal?.number
  const multi =
    data?.multi_strong_candidates ||
    data?.alternatives?.map((a) => a.number) ||
    []
  const nodes = data?.graph?.nodes || []
  const companions = nodes
    .filter((x) => String(x.role || '').toLowerCase().includes('compan') || String(x.role || '') === 't1')
    .map((x) => Number(x.number ?? x.id))
    .filter((n) => Number.isFinite(n))
  const confirmers = nodes
    .filter((x) => String(x.role || '').toLowerCase().includes('confirm') || String(x.role || '') === 't2')
    .map((x) => Number(x.number ?? x.id))
    .filter((n) => Number.isFinite(n))

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-blue-700">Lottery IA</p>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Analizar números</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              Obtenga la recomendación del motor con sus relaciones principales. {DISCLAIMER}
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/lottery">Volver al inicio</Link>
          </Button>
        </div>

        <Card className="border-blue-100 shadow-sm">
          <CardContent className="flex flex-wrap items-end gap-3 pt-6">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Número</label>
              <Input
                value={number}
                onChange={(e) => setNumber(e.target.value)}
                className="w-28"
                inputMode="numeric"
                disabled={busy}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Con (opcional)</label>
              <Input
                value={companion}
                onChange={(e) => setCompanion(e.target.value)}
                className="w-28"
                inputMode="numeric"
                disabled={busy}
                placeholder="ej. 14"
              />
            </div>
            <Button className="bg-blue-600 hover:bg-blue-700" disabled={busy} onClick={() => void run()}>
              {busy ? 'Analizando información…' : 'Analizar'}
            </Button>
          </CardContent>
        </Card>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        {data && (
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-blue-100 md:col-span-2">
              <CardHeader>
                <CardTitle className="text-base text-slate-900">Recomendación principal</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-4">
                {primary != null ? (
                  <LotteryNumberLink number={primary} size="lg" />
                ) : (
                  <p className="text-sm text-slate-600">No hay recomendación principal para este caso.</p>
                )}
                <div className="space-y-1 text-sm text-slate-600">
                  <p>
                    <span className="font-medium text-slate-900">Analizado:</span>{' '}
                    {(data.observed_numbers || []).join(' + ') || number}
                  </p>
                  <p>{data.explanation?.summary || data.primary_signal?.reason || 'Resultado calculado por el motor.'}</p>
                  {multi.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-2">
                      <span className="text-xs font-medium uppercase text-amber-700">Alternativas</span>
                      {multi.map((m) => (
                        <LotteryNumberLink
                          key={m}
                          number={m}
                          size="sm"
                          className="bg-amber-500 hover:bg-amber-600"
                        />
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base">Relaciones de Tabla 1</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {companions.length ? (
                  companions.map((n) => <LotteryNumberLink key={`t1-${n}`} number={n} size="sm" />)
                ) : (
                  <p className="text-sm text-slate-600">Compañeros disponibles en Patrones y tablas.</p>
                )}
                <p className="w-full text-xs text-slate-500">
                  Relaciona cada número con sus compañeros principales.
                </p>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/lottery/admin/control-center/motor/table1">Abrir Tabla 1</Link>
                </Button>
              </CardContent>
            </Card>

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base">Confirmaciones de Tabla 2</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {confirmers.length ? (
                  confirmers.map((n) => <LotteryNumberLink key={`t2-${n}`} number={n} size="sm" />)
                ) : (
                  <p className="text-sm text-slate-600">Confirmadores disponibles en Patrones y tablas.</p>
                )}
                <p className="w-full text-xs text-slate-500">
                  Confirma y amplía las relaciones encontradas en Tabla 1.
                </p>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/lottery/admin/control-center/motor/table2">Abrir Tabla 2</Link>
                </Button>
              </CardContent>
            </Card>

            <details className="md:col-span-2 rounded-lg border border-slate-200 bg-white p-4 text-sm">
              <summary className="cursor-pointer font-medium text-slate-800">Ver detalles del análisis</summary>
              <pre className="mt-3 max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-700">
                {JSON.stringify(data, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </AppShell>
  )
}
