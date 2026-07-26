'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { LotteryNumberLink } from '@/components/lottery/lottery-number-link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import { canAccessLotteryModule, DISCLAIMER, PRODUCT_SEVEN_LOTTERY_NAMES } from '@/lib/lottery'

type Row = {
  lottery?: string
  lottery_id?: string
  date?: string | null
  primera?: string | null
  segunda?: string | null
  tercera?: string | null
  hora?: string | null
}

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function yesterdayIso(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function fmtDate(v: unknown): string {
  if (!v) return '—'
  try {
    return new Date(`${String(v)}T12:00:00`).toLocaleDateString('es-DO', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return String(v)
  }
}

function fmtHora(v: unknown): string {
  if (!v) return ''
  const s = String(v)
  return s.length >= 5 ? s.slice(0, 5) : s
}

export default function ResultadosPage() {
  const router = useRouter()
  const search = useSearchParams()
  const [rows, setRows] = useState<Row[]>([])
  const [lotteries, setLotteries] = useState<{ id: string; name: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const [date, setDate] = useState(search.get('date') || todayIso())
  const [lottery, setLottery] = useState(search.get('lottery') || '')
  const [number, setNumber] = useState(search.get('number') || '')
  const [busy, setBusy] = useState(false)
  const [fallbackCards, setFallbackCards] = useState<Row[]>([])

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError('Sin permiso para consultar resultados.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (date) params.date = date
      if (lottery) params.lottery = lottery
      if (number) params.number = number
      const [list, lots, dash] = await Promise.all([
        apiClient.getLotteryResultados(params),
        apiClient.getLotteryResultadosLotteries().catch(() => ({ items: [] as unknown[] })),
        number || lottery
          ? Promise.resolve(null)
          : apiClient.getLotteryIaDashboard().catch(() => null),
      ])
      setRows((list.items || []) as Row[])
      setLotteries(
        ((lots.items || []) as { id: string; name: string }[]).map((l) => ({
          id: l.id,
          name: l.name,
        })),
      )
      const recent = ((dash as { loterias_recientes?: Row[] } | null)?.loterias_recientes ||
        []) as Row[]
      setFallbackCards(recent)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'No fue posible consultar los resultados. Intente nuevamente.',
      )
    } finally {
      setBusy(false)
    }
  }, [router, date, lottery, number])

  useEffect(() => {
    void load()
  }, [load])

  const cards = useMemo(() => {
    if (rows.length) {
      const rank = new Map(PRODUCT_SEVEN_LOTTERY_NAMES.map((n, i) => [n.toLowerCase(), i]))
      return [...rows].sort((a, b) => {
        const ra = rank.get(String(a.lottery || '').toLowerCase()) ?? 99
        const rb = rank.get(String(b.lottery || '').toLowerCase()) ?? 99
        return ra - rb || String(b.date || '').localeCompare(String(a.date || ''))
      })
    }
    // Sin resultados del día: mostrar último disponible (sin errores técnicos)
    if (!number && !lottery) return fallbackCards
    return []
  }, [rows, fallbackCards, number, lottery])

  const withResults = cards.filter((c) => c.primera || c.segunda || c.tercera).length
  const usingFallback = !rows.length && cards === fallbackCards && !number
  const statusLabel = usingFallback
    ? 'Mostrando el último sorteo disponible de cada lotería'
    : withResults > 0
      ? 'Actualizado'
      : 'Sin resultados para la fecha seleccionada'

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="rounded-2xl bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 px-6 py-7 text-white shadow-md">
          <p className="text-sm font-medium text-blue-100">Lottery IA</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Resultados e histórico</h1>
          <p className="mt-2 max-w-2xl text-sm text-blue-50">
            Consulte los sorteos recientes o busque resultados anteriores.
          </p>
          <p className="mt-2 text-xs text-blue-100/90">{DISCLAIMER}</p>
        </div>

        <Card className="border-blue-100">
          <CardContent className="space-y-4 pt-6">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Fecha</label>
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-44"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Lotería</label>
                <select
                  className="h-10 min-w-[12rem] rounded-md border border-input bg-background px-3 text-sm"
                  value={lottery}
                  onChange={(e) => setLottery(e.target.value)}
                >
                  <option value="">Todas las activas</option>
                  {lotteries.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">
                  Buscar número
                </label>
                <Input
                  value={number}
                  onChange={(e) => setNumber(e.target.value)}
                  className="w-28"
                  inputMode="numeric"
                  placeholder="1–100"
                />
              </div>
              <Button className="bg-blue-600 hover:bg-blue-700" disabled={busy} onClick={() => void load()}>
                {busy ? 'Consultando…' : 'Consultar'}
              </Button>
              <Button variant="outline" onClick={() => setDate(todayIso())}>
                Hoy
              </Button>
              <Button variant="outline" onClick={() => setDate(yesterdayIso())}>
                Ayer
              </Button>
              <Button variant="outline" asChild>
                <Link href="/lottery">Volver al inicio</Link>
              </Button>
            </div>

            <div className="flex flex-wrap gap-4 text-sm">
              <p>
                <span className="text-slate-500">Fecha seleccionada:</span>{' '}
                <span className="font-medium text-blue-900">{fmtDate(date)}</span>
              </p>
              <p>
                <span className="text-slate-500">Estado:</span>{' '}
                <span className="font-medium text-slate-800">{statusLabel}</span>
              </p>
              <p>
                <span className="text-slate-500">Loterías con resultados:</span>{' '}
                <span className="font-medium">{withResults}</span>
              </p>
            </div>
          </CardContent>
        </Card>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((row, idx) => (
            <Card key={`${row.lottery}-${row.date}-${idx}`} className="border-blue-100">
              <CardContent className="space-y-3 pt-5">
                <div>
                  <p className="font-semibold text-slate-900">{row.lottery || '—'}</p>
                  <p className="text-sm text-slate-500">
                    {fmtDate(row.date)}
                    {row.hora ? ` · ${fmtHora(row.hora)}` : ''}
                  </p>
                  {usingFallback && (
                    <p className="mt-1 text-xs font-medium text-amber-700">Último disponible</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <LotteryNumberLink
                    number={String(row.primera || '')}
                    size="lg"
                    lottery={row.lottery}
                    date={row.date}
                    position="primera"
                  />
                  <LotteryNumberLink
                    number={String(row.segunda || '')}
                    size="lg"
                    lottery={row.lottery}
                    date={row.date}
                    position="segunda"
                    className="bg-sky-600 hover:bg-sky-700"
                  />
                  <LotteryNumberLink
                    number={String(row.tercera || '')}
                    size="lg"
                    lottery={row.lottery}
                    date={row.date}
                    position="tercera"
                    className="bg-indigo-600 hover:bg-indigo-700"
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {!busy && !cards.length && !error && (
          <p className="text-sm text-slate-600">
            No hay resultados para los filtros seleccionados.
          </p>
        )}
      </div>
    </AppShell>
  )
}
