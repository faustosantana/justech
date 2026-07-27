'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { LotteryNumberLink } from '@/components/lottery/lottery-number-link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import {
  buildCrossNarrative,
  isOfficialStrong,
  pad2,
  signalHeadline,
  supportLevel,
  supportTone,
} from '@/lib/lottery-analysis-present'
import { canAccessLotteryAdmin, canAccessLotteryModule, DISCLAIMER } from '@/lib/lottery'

type SameDayCross = {
  observed_x?: number
  companion_c?: number
  confirmer_y?: number
  date?: string
  lottery_x?: string | null
  lottery_y?: string | null
  position_x?: string | null
  position_y?: string | null
  table1_route?: string
  table2_route?: string
}

type DayLotteryRow = {
  lottery?: string
  primera?: string | number | null
  segunda?: string | number | null
  tercera?: string | number | null
  draw_id?: string | null
}

type Analysis = {
  primary_signal?: {
    number?: number
    reason?: string
    classification?: string
    analytical_confidence?: number
    score?: number
    table1_sources?: number[]
    table2_confirmers?: number[]
    same_day_cross_support?: boolean
  } | null
  alternatives?: { number: number; classification?: string; score?: number }[]
  multi_strong_candidates?: number[]
  ranked_candidates?: {
    number: number
    classification?: string
    classification_reason?: string
    total_score?: number
    analytical_confidence?: number
  }[]
  explanation?: {
    summary?: string
    body?: Record<string, unknown>
    relation_direct?: string
    confirmation_external?: string
    conclusion?: string
    evidence_current?: string
    historical_behavior?: string
    comparison?: string
    warning?: string
  }
  observed_numbers?: number[]
  derivations?: { path?: number[]; via?: string; numbers?: number[] }[]
  same_day_context?: {
    date?: string
    confirmer_numbers?: number[]
    by_lottery?: Record<string, DayLotteryRow>
    appearances?: {
      number?: number
      lottery?: string
      position?: string
    }[]
  } | null
  same_day_cross?: SameDayCross[]
  historical_evidence?: {
    period_label?: string
    date_from?: string | null
    date_to?: string | null
    level1_count?: number
    level2_count?: number
    level3_count?: number
    metrics?: {
      exact_cases?: number
      exact_hits?: number
      t1_family_hits?: number
      t2_neighbor_hits?: number
      d1_hits?: number
      d3_hits?: number
      d7_hits?: number
      evidence_quantity?: string
      evidence_quantity_message?: string
      recent_cases?: {
        date?: string
        observed?: number[]
        candidate?: number
        result?: string
        window?: string
      }[]
    }
    evidence_card?: Record<string, unknown>
    rival_card?: Record<string, unknown> | null
    comparison?: string
    narrative?: {
      conclusion?: string
      evidence_current?: string
      historical_behavior?: string
      comparison?: string
      warning?: string
    }
  } | null
  graph?: {
    nodes?: { id?: string; number?: number; role?: string }[]
    edges?: { source?: number; target?: number; relation?: string; type?: string }[]
  }
}

function dayChipClass(role: 'observed' | 'confirmer' | 'companion' | 'plain'): string {
  if (role === 'observed') return 'bg-blue-600 hover:bg-blue-700 ring-2 ring-offset-2 ring-blue-300'
  if (role === 'confirmer') return 'bg-emerald-600 hover:bg-emerald-700 ring-2 ring-offset-2 ring-emerald-300'
  if (role === 'companion') return 'bg-orange-500 hover:bg-orange-600 ring-2 ring-offset-2 ring-orange-300'
  return 'bg-slate-400 hover:bg-slate-500'
}

type HistRow = {
  date?: string
  fecha?: string
  lottery_name?: string
  lottery?: string
  loteria?: string
  position?: string | number
  primera?: string
  segunda?: string
  tercera?: string
  co_numbers?: number[]
  numbers?: number[]
  draw_numbers?: number[]
  candidatos_confirmados?: number[]
  texto?: string
  estado?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

function extractGroup(detail: Record<string, unknown> | null | undefined): {
  code: number | null
  members: number[]
} {
  if (!detail) return { code: null, members: [] }
  const nested = (detail.detail || {}) as Record<string, unknown>
  const code = Number(nested.code ?? detail.code)
  const raw =
    (nested.group_members as number[]) ||
    (detail.group_numbers as number[]) ||
    (detail.group_members as number[]) ||
    []
  const members = (Array.isArray(raw) ? raw : [])
    .map((x) => Number(x))
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 100)
  return {
    code: Number.isFinite(code) ? code : null,
    members,
  }
}

export default function LotteryAnalizarPage() {
  const router = useRouter()
  const search = useSearchParams()
  const isAdmin = canAccessLotteryAdmin(getUserRole())

  const [number, setNumber] = useState(search.get('number') || '')
  const [companion, setCompanion] = useState(search.get('with') || '')
  const ctxLottery = search.get('lottery') || ''
  const ctxDate = search.get('date') || ''
  const ctxPosition = search.get('position') || ''
  const [analysisDate, setAnalysisDate] = useState(ctxDate)
  const [histPeriod, setHistPeriod] = useState('all')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Analysis | null>(null)
  const [t1, setT1] = useState<{ code: number | null; members: number[] }>({
    code: null,
    members: [],
  })
  const [t2, setT2] = useState<{ code: number | null; members: number[] }>({
    code: null,
    members: [],
  })
  const [history, setHistory] = useState<HistRow[]>([])
  const [historyMeta, setHistoryMeta] = useState<{ cases?: number; period?: string }>({})
  const [drawPeers, setDrawPeers] = useState<{
    primera?: string
    segunda?: string
    tercera?: string
  } | null>(null)
  const [prevStack, setPrevStack] = useState<string[]>([])

  const loadTables = useCallback(async (n: number) => {
    try {
      const [a, b] = await Promise.all([
        apiClient.getLotteryNumericRelationsNumber(n, 'table1'),
        apiClient.getLotteryNumericRelationsNumber(n, 'table2'),
      ])
      setT1(extractGroup(a))
      setT2(extractGroup(b))
    } catch {
      setT1({ code: null, members: [] })
      setT2({ code: null, members: [] })
    }
  }, [])

  const loadHistory = useCallback(async (n: number) => {
    try {
      const lots = await apiClient.getLotteryNumericRelationsLotteries()
      const ids = (lots.items || []).map((x) => x.id).filter(Boolean)
      if (!ids.length) {
        setHistory([])
        setHistoryMeta({})
        return
      }
      const res = await apiClient.postLotteryNrNumberOccurrences({
        number: n,
        scope: {
          primary_lottery_ids: ids,
          confirming_lottery_ids: ids,
          follow_up_lottery_ids: ids,
        },
        confirmation_window: { mode: 'SAME_DRAW', timezone: 'America/Santo_Domingo' },
        max_horizon: 5,
        page: 1,
        page_size: 8,
        order: 'desc',
      })
      const items = (res.items || res.occurrences || res.rows || []) as HistRow[]
      setHistory(Array.isArray(items) ? items.slice(0, 8) : [])
      setHistoryMeta({
        cases: Number(res.total ?? res.count ?? items.length) || items.length,
        period: 'Universo activo · últimas apariciones',
      })
    } catch {
      setHistory([])
      setHistoryMeta({})
    }
  }, [])

  const loadDrawContext = useCallback(async () => {
    if (!ctxLottery || !ctxDate) {
      setDrawPeers(null)
      return
    }
    try {
      const list = await apiClient.getLotteryResultados({
        date: ctxDate,
        lottery: ctxLottery,
      })
      const row = (list.items || [])[0] as
        | { primera?: string; segunda?: string; tercera?: string }
        | undefined
      if (row) setDrawPeers(row)
      else setDrawPeers(null)
    } catch {
      setDrawPeers(null)
    }
  }, [ctxLottery, ctxDate])

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
      if (w && (!Number.isInteger(Number(w)) || Number(w) < 1 || Number(w) > 100)) {
        setError('El número confirmador debe estar entre 1 y 100.')
        return
      }
      const dateForRun = (analysisDate || ctxDate || '').trim() || undefined
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
            numbers: [n],
            same_day_confirmers: w ? [Number(w)] : undefined,
            mode: 'socio',
            derivation_depth: 0,
            create_signals: false,
            explanation_level: 'analitico',
            date: dateForRun,
            lottery: ctxLottery || undefined,
            positions: ['first'],
            historical_period: histPeriod,
            include_historical: true,
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
        const json = (await res.json()) as Analysis
        setData(json)
        await Promise.all([loadTables(n), loadHistory(n), loadDrawContext()])
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
    [
      number,
      companion,
      router,
      ctxDate,
      ctxLottery,
      analysisDate,
      histPeriod,
      loadTables,
      loadHistory,
      loadDrawContext,
    ],
  )

  useEffect(() => {
    if (search.get('auto') === '1' && search.get('number')) {
      void run(search.get('number') || undefined, search.get('with') || undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const observed = Number(String(number).replace(/\D/g, '')) || data?.observed_numbers?.[0]
  const primary = data?.primary_signal
  const classification = primary?.classification
  const headline = signalHeadline(classification)
  const level = supportLevel(primary?.analytical_confidence, primary?.score)
  const alts = useMemo(() => {
    const fromMulti = data?.multi_strong_candidates || []
    const fromAlt = (data?.alternatives || []).map((a) => a.number)
    const merged = [...fromMulti, ...fromAlt].filter(
      (n) => n != null && n !== primary?.number,
    )
    return Array.from(new Set(merged)).slice(0, 6)
  }, [data, primary?.number])

  const t1Companions = t1.members.filter((n) => n !== observed)
  const t2Neighbors = t2.members.filter((n) => n !== observed)

  const narrative = useMemo(() => {
    if (!observed || !data) return ''
    const derivations = (data.derivations || []).map((d) => ({
      path: d.path || d.numbers || [],
      via: d.via,
    }))
    return buildCrossNarrative({
      observed,
      t1Companions,
      t1Code: t1.code,
      t2Neighbors,
      t2Code: t2.code,
      primary: primary?.number,
      classification,
      reason: primary?.reason || data.explanation?.summary,
      alternatives: alts,
      derivations,
    })
  }, [observed, data, t1Companions, t1.code, t2Neighbors, t2.code, primary, classification, alts])

  const analyzeNumber = (n: number, opts?: { date?: string; lottery?: string; position?: string }) => {
    if (observed) setPrevStack((s) => [...s, String(observed)])
    setNumber(String(n))
    setCompanion('')
    const d = opts?.date || analysisDate || ctxDate
    if (d) setAnalysisDate(d)
    const params = new URLSearchParams()
    params.set('number', String(n))
    params.set('auto', '1')
    if (d) params.set('date', d)
    if (opts?.lottery || ctxLottery) params.set('lottery', opts?.lottery || ctxLottery)
    if (opts?.position || ctxPosition) params.set('position', opts?.position || ctxPosition)
    router.push(`/lottery/analizar?${params.toString()}`)
    void run(String(n), '')
  }

  const confirmerSet = useMemo(() => {
    const fromCross = (data?.same_day_cross || []).map((c) => Number(c.confirmer_y))
    const fromPrimary = data?.primary_signal?.table2_confirmers || []
    return new Set([...fromCross, ...fromPrimary].filter((x) => Number.isFinite(x)))
  }, [data])

  const companionSet = useMemo(() => {
    const fromCross = (data?.same_day_cross || []).map((c) => Number(c.companion_c))
    if (primary?.number != null) fromCross.push(primary.number)
    return new Set(fromCross.filter((x) => Number.isFinite(x)))
  }, [data, primary?.number])

  const dayRole = (n: number): 'observed' | 'confirmer' | 'companion' | 'plain' => {
    if (n === observed) return 'observed'
    if (confirmerSet.has(n)) return 'confirmer'
    if (companionSet.has(n)) return 'companion'
    return 'plain'
  }

  const dayLotteries = useMemo(() => {
    const by = data?.same_day_context?.by_lottery
    if (!by) return [] as DayLotteryRow[]
    return Object.values(by)
  }, [data])

  const chatHref = useMemo(() => {
    const n = observed || number
    const params = new URLSearchParams()
    params.set('q', `Explícame el análisis completo del ${n}.`)
    if (n) params.set('number', String(n))
    if (ctxLottery) params.set('lottery', ctxLottery)
    if (ctxDate) params.set('date', ctxDate)
    if (primary?.number) params.set('highlight', String(primary.number))
    return `/lottery/chat?${params.toString()}`
  }, [observed, number, ctxLottery, ctxDate, primary?.number])

  const patternHref = useMemo(() => {
    const n = observed || number
    const cand = t1Companions[0]
    const params = new URLSearchParams()
    if (n) params.set('number', String(n))
    if (cand) params.set('candidate', String(cand))
    return `/lottery/admin/control-center/motor/patron?${params.toString()}`
  }, [observed, number, t1Companions])

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <div className="rounded-2xl bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 px-6 py-7 text-white shadow-md">
          <p className="text-sm font-medium text-blue-100">Lottery IA</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Analizar números</h1>
          <p className="mt-2 max-w-2xl text-sm text-blue-50">
            Revise las relaciones de Tabla 1, Tabla 2 y el comportamiento histórico. {DISCLAIMER}
          </p>
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
            <div className="min-w-[12rem] flex-1">
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Número confirmador del mismo día (opcional)
              </label>
              <Input
                value={companion}
                onChange={(e) => setCompanion(e.target.value)}
                className="w-28"
                inputMode="numeric"
                disabled={busy}
                placeholder="ej. 14"
              />
              <p className="mt-1 max-w-sm text-[11px] leading-snug text-slate-500">
                Use este campo para indicar otro número que salió el mismo día y comprobar si
                fortalece a un compañero de Tabla 1.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Fecha</label>
              <Input
                id="analysis-date-input"
                type="date"
                value={analysisDate}
                onChange={(e) => setAnalysisDate(e.target.value)}
                className="w-40"
                disabled={busy}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Período histórico
              </label>
              <select
                className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm"
                value={histPeriod}
                disabled={busy}
                onChange={(e) => setHistPeriod(e.target.value)}
              >
                <option value="all">Todo el histórico</option>
                <option value="5y">Últimos 5 años</option>
                <option value="3y">Últimos 3 años</option>
                <option value="1y">Último año</option>
              </select>
            </div>
            <Button className="bg-blue-600 hover:bg-blue-700" disabled={busy} onClick={() => void run()}>
              {busy ? 'Analizando información…' : 'Analizar'}
            </Button>
            {!analysisDate && !ctxDate && (
              <Button
                variant="outline"
                disabled={busy || !number}
                onClick={() => {
                  const el = document.getElementById('analysis-date-input')
                  el?.focus()
                }}
              >
                Analizar con resultados de una fecha
              </Button>
            )}
            <Button variant="outline" asChild>
              <Link href="/lottery">Volver al inicio</Link>
            </Button>
          </CardContent>
        </Card>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {data && observed ? (
          <div className="space-y-4">
            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base text-blue-900">Número analizado</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-start gap-4">
                <LotteryNumberLink number={observed} size="lg" />
                <div className="space-y-1 text-sm text-slate-600">
                  {(ctxLottery || ctxDate || ctxPosition) && (
                    <>
                      {ctxLottery && (
                        <p>
                          <span className="font-medium text-slate-900">Lotería:</span> {ctxLottery}
                        </p>
                      )}
                      {ctxDate && (
                        <p>
                          <span className="font-medium text-slate-900">Fecha:</span> {ctxDate}
                        </p>
                      )}
                      {ctxPosition && (
                        <p>
                          <span className="font-medium text-slate-900">Posición:</span> {ctxPosition}
                        </p>
                      )}
                    </>
                  )}
                  {drawPeers && (
                    <div className="flex flex-wrap items-center gap-2 pt-2">
                      <span className="text-xs font-medium uppercase text-slate-500">
                        Mismo sorteo
                      </span>
                      {(['primera', 'segunda', 'tercera'] as const).map((pos) => {
                        const val = drawPeers[pos]
                        if (!val) return null
                        return (
                          <LotteryNumberLink
                            key={pos}
                            number={val}
                            size="sm"
                            lottery={ctxLottery}
                            date={ctxDate}
                            position={pos}
                            className={
                              Number(val) === observed
                                ? 'ring-2 ring-offset-2 ring-blue-400'
                                : undefined
                            }
                          />
                        )
                      })}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base text-blue-900">{headline}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-start gap-4">
                {primary?.number != null ? (
                  <LotteryNumberLink
                    number={primary.number}
                    size="lg"
                    className={
                      isOfficialStrong(classification)
                        ? 'bg-emerald-600 hover:bg-emerald-700'
                        : 'bg-amber-500 hover:bg-amber-600'
                    }
                  />
                ) : (
                  <p className="text-sm text-slate-600">
                    No hay una señal destacada para este caso.
                  </p>
                )}
                <div className="min-w-[14rem] flex-1 space-y-2 text-sm text-slate-600">
                  <p>
                    {data.explanation?.summary ||
                      primary?.reason ||
                      'Resultado calculado a partir de las tablas del motor.'}
                  </p>
                  <span
                    className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${supportTone(level)}`}
                  >
                    Respaldo: {level}
                  </span>
                  {!isOfficialStrong(classification) && primary?.number != null && (
                    <p className="text-xs text-amber-800">
                      Esta señal no se eleva a fuerte oficial T1×T2; se muestra como relación
                      destacada del análisis.
                    </p>
                  )}
                  {alts.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="text-xs font-medium uppercase text-amber-700">
                        Alternativas
                      </span>
                      {alts.map((m) => (
                        <button key={m} type="button" onClick={() => analyzeNumber(m)}>
                          <LotteryNumberLink
                            number={m}
                            size="sm"
                            className="bg-amber-500 hover:bg-amber-600 pointer-events-none"
                          />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border-sky-100 bg-sky-50/40">
                <CardHeader>
                  <CardTitle className="text-base text-blue-900">Tabla 1 — Compañeros</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p className="text-slate-600">
                    Tabla 1 identifica los números que comparten la misma relación matemática.
                  </p>
                  <p>
                    <span className="text-slate-500">Número observado:</span>{' '}
                    <span className="font-semibold text-slate-900">{pad2(observed)}</span>
                    {t1.code != null && (
                      <>
                        {' · '}
                        <span className="text-slate-500">Código:</span>{' '}
                        <span className="font-semibold text-slate-900">{t1.code}</span>
                      </>
                    )}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {t1Companions.length ? (
                      t1Companions.map((n) => (
                        <button key={`t1-${n}`} type="button" onClick={() => analyzeNumber(n)}>
                          <span className="inline-flex min-h-10 min-w-10 cursor-pointer items-center justify-center rounded-full bg-sky-600 text-base font-bold text-white shadow-sm transition hover:scale-105 hover:bg-sky-700">
                            {pad2(n)}
                          </span>
                        </button>
                      ))
                    ) : (
                      <p className="text-slate-600">No hay otros compañeros en este grupo.</p>
                    )}
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/lottery/admin/control-center/motor/table1">
                      Ver Tabla 1 completa
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-emerald-100 bg-emerald-50/30">
                <CardHeader>
                  <CardTitle className="text-base text-blue-900">
                    Tabla 2 — Confirmaciones y vecinos
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p className="text-slate-600">
                    Tabla 2 confirma y amplía las relaciones encontradas en Tabla 1.
                  </p>
                  <p>
                    <span className="text-slate-500">Relación con:</span>{' '}
                    <span className="font-semibold text-slate-900">{pad2(observed)}</span>
                    {t2.code != null && (
                      <>
                        {' · '}
                        <span className="text-slate-500">Código:</span>{' '}
                        <span className="font-semibold text-slate-900">{t2.code}</span>
                      </>
                    )}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {t2Neighbors.length ? (
                      t2Neighbors.map((n) => (
                        <button key={`t2-${n}`} type="button" onClick={() => analyzeNumber(n)}>
                          <span className="inline-flex min-h-10 min-w-10 cursor-pointer items-center justify-center rounded-full bg-emerald-600 text-base font-bold text-white shadow-sm transition hover:scale-105 hover:bg-emerald-700">
                            {pad2(n)}
                          </span>
                        </button>
                      ))
                    ) : (
                      <p className="text-slate-600">No hay vecinos adicionales en este grupo.</p>
                    )}
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/lottery/admin/control-center/motor/table2">
                      Ver Tabla 2 completa
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </div>

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base text-blue-900">Cruce del mismo día</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-slate-700">
                {!analysisDate && !ctxDate && !data?.same_day_context ? (
                  <p className="text-slate-600">
                    No hay contexto diario. Elija una fecha o use el número confirmador del mismo
                    día para cruzar loterías.
                  </p>
                ) : (data?.same_day_cross || []).length === 0 ? (
                  <p className="text-slate-600">
                    No se encontraron confirmaciones entre otras loterías de esta fecha.
                  </p>
                ) : (
                  (data?.same_day_cross || []).map((c, idx) => (
                    <div
                      key={`${c.companion_c}-${c.confirmer_y}-${idx}`}
                      className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4"
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="text-center">
                          <p className="text-[10px] uppercase text-slate-500">Origen</p>
                          <span className="mt-1 inline-flex min-h-10 min-w-10 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                            {pad2(c.observed_x)}
                          </span>
                        </div>
                        <span className="text-slate-400">→ Tabla 1 →</span>
                        <div className="text-center">
                          <p className="text-[10px] uppercase text-slate-500">Compañero</p>
                          <span className="mt-1 inline-flex min-h-10 min-w-10 items-center justify-center rounded-full bg-orange-500 text-sm font-bold text-white">
                            {pad2(c.companion_c)}
                          </span>
                        </div>
                        <span className="text-slate-400">← Tabla 2 ←</span>
                        <div className="text-center">
                          <p className="text-[10px] uppercase text-slate-500">Confirmador</p>
                          <span className="mt-1 inline-flex min-h-10 min-w-10 items-center justify-center rounded-full bg-emerald-600 text-sm font-bold text-white">
                            {pad2(c.confirmer_y)}
                          </span>
                        </div>
                      </div>
                      <div className="mt-3 space-y-1 text-xs text-slate-600">
                        <p>
                          Confirmación de Tabla 2:{' '}
                          <span className="font-medium text-slate-900">
                            {pad2(c.confirmer_y)} → {pad2(c.companion_c)}
                          </span>
                        </p>
                        <p>
                          Loterías:{' '}
                          <span className="font-medium text-slate-900">
                            {c.lottery_x || '—'} · {c.lottery_y || '—'}
                          </span>
                        </p>
                        <p>
                          Resultado:{' '}
                          <span className="font-semibold text-emerald-800">
                            {pad2(c.companion_c)} fortalecido
                          </span>
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {data.historical_evidence && (
              <>
                <Card className="border-indigo-100">
                  <CardHeader>
                    <CardTitle className="text-base text-blue-900">Evidencias actuales</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm text-slate-700">
                    {(() => {
                      const card = data.historical_evidence?.evidence_card || {}
                      return (
                        <ul className="grid gap-2 sm:grid-cols-2">
                          <li>
                            Tabla 1:{' '}
                            <span className="font-medium">
                              {card.table1_support ? 'sí' : 'no'}
                            </span>
                          </li>
                          <li>
                            Tabla 2:{' '}
                            <span className="font-medium">
                              {card.table2_support ? 'sí' : 'no'}
                            </span>
                          </li>
                          <li>
                            Cruce del mismo día:{' '}
                            <span className="font-medium">
                              {card.same_day_cross_support ? 'sí' : 'no'}
                            </span>
                          </li>
                          <li>
                            Loterías involucradas:{' '}
                            <span className="font-medium">
                              {Number(card.independent_lotteries) || 0}
                            </span>
                          </li>
                          <li>
                            Rutas independientes:{' '}
                            <span className="font-medium">
                              {Number(card.independent_routes) || 0}
                            </span>
                          </li>
                        </ul>
                      )
                    })()}
                    {data.explanation?.evidence_current && (
                      <p className="pt-1 text-slate-600">{data.explanation.evidence_current}</p>
                    )}
                  </CardContent>
                </Card>

                <Card className="border-indigo-100">
                  <CardHeader>
                    <CardTitle className="text-base text-blue-900">
                      Comportamiento histórico
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <p className="text-xs text-slate-500">
                      {data.historical_evidence.period_label || 'Todo el histórico'}
                      {data.historical_evidence.date_from
                        ? ` · ${data.historical_evidence.date_from} → ${data.historical_evidence.date_to}`
                        : data.historical_evidence.date_to
                          ? ` · hasta ${data.historical_evidence.date_to}`
                          : ''}
                    </p>
                    {(() => {
                      const m = data.historical_evidence?.metrics || {}
                      const tiles = [
                        { label: 'Casos equivalentes', value: m.exact_cases },
                        { label: 'Aciertos exactos', value: m.exact_hits },
                        { label: 'Familia Tabla 1', value: m.t1_family_hits },
                        { label: 'Vecinos Tabla 2', value: m.t2_neighbor_hits },
                        { label: 'D+1', value: m.d1_hits },
                        { label: 'D+3', value: m.d3_hits },
                        { label: 'D+7', value: m.d7_hits },
                      ]
                      return (
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                          {tiles.map((t) => (
                            <div
                              key={t.label}
                              className="rounded-xl border border-indigo-50 bg-indigo-50/40 px-3 py-2"
                            >
                              <p className="text-[10px] uppercase tracking-wide text-slate-500">
                                {t.label}
                              </p>
                              <p className="text-lg font-semibold text-slate-900">
                                {t.value ?? 0}
                              </p>
                            </div>
                          ))}
                        </div>
                      )
                    })()}
                    <p className="text-slate-700">
                      {data.historical_evidence.narrative?.historical_behavior ||
                        data.historical_evidence.metrics?.evidence_quantity_message}
                    </p>
                    {(data.historical_evidence.level2_count || 0) > 0 && (
                      <p className="text-xs text-slate-500">
                        Ruta ampliada (otros confirmadores):{' '}
                        {data.historical_evidence.level2_count} casos · Evidencia estructural
                        (nivel 3): {data.historical_evidence.level3_count || 0}
                      </p>
                    )}
                  </CardContent>
                </Card>

                {(data.historical_evidence.metrics?.recent_cases || []).length > 0 && (
                  <Card className="border-indigo-100">
                    <CardHeader>
                      <CardTitle className="text-base text-blue-900">Casos recientes</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto rounded-lg border border-indigo-50">
                        <table className="min-w-full text-left text-sm">
                          <thead className="bg-indigo-50 text-xs uppercase text-blue-900">
                            <tr>
                              <th className="px-3 py-2">Fecha</th>
                              <th className="px-3 py-2">Números observados</th>
                              <th className="px-3 py-2">Candidato</th>
                              <th className="px-3 py-2">Resultado posterior</th>
                              <th className="px-3 py-2">Ventana</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(data.historical_evidence.metrics?.recent_cases || [])
                              .slice(0, 10)
                              .map((c, i) => (
                                <tr key={`${c.date}-${i}`} className="border-t border-indigo-50">
                                  <td className="px-3 py-2">{c.date}</td>
                                  <td className="px-3 py-2">
                                    {(c.observed || []).map((n) => pad2(n)).join(' · ')}
                                  </td>
                                  <td className="px-3 py-2">{pad2(c.candidate)}</td>
                                  <td className="px-3 py-2">{c.result}</td>
                                  <td className="px-3 py-2">{c.window || '—'}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {data.historical_evidence.rival_card && (
                  <Card className="border-amber-100">
                    <CardHeader>
                      <CardTitle className="text-base text-blue-900">Comparación</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm text-slate-700">
                      <div className="grid gap-3 md:grid-cols-2">
                        {[
                          data.historical_evidence.evidence_card,
                          data.historical_evidence.rival_card,
                        ].map((card) => {
                          if (!card) return null
                          return (
                            <div
                              key={String(card.candidate_number)}
                              className="rounded-xl border border-slate-100 bg-slate-50/60 p-3"
                            >
                              <p className="mb-2 text-lg font-semibold text-slate-900">
                                {pad2(card.candidate_number as number)}
                              </p>
                              <ul className="space-y-1 text-xs">
                                <li>
                                  Respaldo Tabla 1: {card.table1_support ? 'sí' : 'no'}
                                </li>
                                <li>
                                  Confirmación Tabla 2: {card.table2_support ? 'sí' : 'no'}
                                </li>
                                <li>
                                  Confirmación en otra lotería:{' '}
                                  {card.same_day_cross_support ? 'sí' : 'no'}
                                </li>
                                <li>
                                  Evidencias independientes:{' '}
                                  {Number(card.independent_routes) || 0}
                                </li>
                                <li>
                                  Casos históricos equivalentes:{' '}
                                  {Number(card.exact_historical_cases) || 0}
                                </li>
                                <li>
                                  Aciertos exactos D+1 a D+7: {Number(card.d7_hits) || 0}
                                </li>
                              </ul>
                            </div>
                          )
                        })}
                      </div>
                      <p>
                        {data.historical_evidence.comparison ||
                          data.historical_evidence.narrative?.comparison}
                      </p>
                      <p className="text-xs text-amber-800">
                        {data.historical_evidence.narrative?.warning ||
                          'El histórico describe comportamientos anteriores y no garantiza que el resultado vuelva a repetirse.'}
                      </p>
                    </CardContent>
                  </Card>
                )}
              </>
            )}

            {dayLotteries.length > 0 && (
              <Card className="border-blue-100">
                <CardHeader>
                  <CardTitle className="text-base text-blue-900">
                    Resultados revisados del día
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-3 text-[11px] text-slate-500">
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full bg-blue-600" /> Observado
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" /> Confirmador
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full bg-orange-500" /> Compañero
                      fortalecido
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-400" /> Sin relación
                      directa
                    </span>
                  </div>
                  <div className="overflow-x-auto rounded-lg border border-blue-100">
                    <table className="min-w-full text-left text-sm">
                      <thead className="bg-blue-50 text-xs uppercase text-blue-900">
                        <tr>
                          <th className="px-3 py-2">Lotería</th>
                          <th className="px-3 py-2">Primera</th>
                          <th className="px-3 py-2">Segunda</th>
                          <th className="px-3 py-2">Tercera</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dayLotteries.map((row) => {
                          const lot = row.lottery || '—'
                          const dateS =
                            data?.same_day_context?.date || analysisDate || ctxDate
                          return (
                            <tr key={lot} className="border-t border-blue-50">
                              <td className="px-3 py-2 font-medium text-slate-800">{lot}</td>
                              {(['primera', 'segunda', 'tercera'] as const).map((pos) => {
                                const raw = row[pos]
                                const num = Number(String(raw ?? '').replace(/\D/g, ''))
                                if (!Number.isInteger(num) || num < 1 || num > 100) {
                                  return (
                                    <td key={pos} className="px-3 py-2 text-slate-400">
                                      —
                                    </td>
                                  )
                                }
                                const role = dayRole(num)
                                return (
                                  <td key={pos} className="px-3 py-2">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        analyzeNumber(num, {
                                          date: dateS,
                                          lottery: lot,
                                          position: pos,
                                        })
                                      }
                                    >
                                      <span
                                        className={`inline-flex min-h-8 min-w-8 items-center justify-center rounded-full text-xs font-bold text-white ${dayChipClass(role)}`}
                                      >
                                        {pad2(num)}
                                      </span>
                                    </button>
                                  </td>
                                )
                              })}
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base text-blue-900">Cruce de relaciones</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm leading-relaxed text-slate-700">
                {data.explanation?.relation_direct ||
                data.explanation?.confirmation_external ||
                data.explanation?.conclusion ? (
                  <>
                    {data.explanation.relation_direct && (
                      <p>
                        <span className="font-medium text-slate-900">Relación directa:</span>{' '}
                        {data.explanation.relation_direct}
                      </p>
                    )}
                    {data.explanation.confirmation_external && (
                      <p>
                        <span className="font-medium text-slate-900">Confirmación externa:</span>{' '}
                        {data.explanation.confirmation_external}
                      </p>
                    )}
                    {data.explanation.conclusion && (
                      <p>
                        <span className="font-medium text-slate-900">Conclusión:</span>{' '}
                        {data.explanation.conclusion}
                      </p>
                    )}
                  </>
                ) : (
                  narrative ||
                  'El motor no encontró un cruce suficiente entre Tabla 1 y Tabla 2 para este número.'
                )}
              </CardContent>
            </Card>

            <Card className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-base text-blue-900">Comportamiento histórico</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {history.length ? (
                  <>
                    <p className="text-slate-600">
                      Últimas apariciones del {pad2(observed)}
                      {historyMeta.cases != null ? ` · ${historyMeta.cases} casos revisados` : ''}
                      {historyMeta.period ? ` · ${historyMeta.period}` : ''}
                    </p>
                    <div className="overflow-x-auto rounded-lg border border-blue-100">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-blue-50 text-xs uppercase text-blue-900">
                          <tr>
                            <th className="px-3 py-2">Fecha</th>
                            <th className="px-3 py-2">Lotería</th>
                            <th className="px-3 py-2">Sorteo</th>
                            <th className="px-3 py-2">Relaciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {history.map((row, i) => {
                            const lot = row.lottery_name || row.loteria || row.lottery || '—'
                            const fecha = row.fecha || row.date
                            const nums = (
                              row.candidatos_confirmados ||
                              row.co_numbers ||
                              row.draw_numbers ||
                              row.numbers ||
                              [row.primera, row.segunda, row.tercera]
                            )
                              .map((x) => Number(x))
                              .filter((x) => Number.isInteger(x) && x >= 1 && x <= 100)
                            const t1Hits = nums.filter((x) => t1.members.includes(Number(x)))
                            const t2Hits = nums.filter((x) => t2.members.includes(Number(x)))
                            return (
                              <tr key={i} className="border-t border-slate-100">
                                <td className="px-3 py-2">
                                  {fecha ? (
                                    <Link
                                      className="text-blue-700 underline"
                                      href={`/lottery/resultados?date=${fecha}`}
                                    >
                                      {fecha}
                                    </Link>
                                  ) : (
                                    '—'
                                  )}
                                </td>
                                <td className="px-3 py-2">{lot}</td>
                                <td className="px-3 py-2">
                                  <div className="flex flex-wrap gap-1">
                                    {(nums.length ? nums : [observed]).slice(0, 5).map((n) => (
                                      <button
                                        key={`${i}-${n}`}
                                        type="button"
                                        onClick={() => analyzeNumber(Number(n))}
                                        className="inline-flex min-h-7 min-w-7 cursor-pointer items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white hover:bg-blue-700"
                                        title="Analizar número"
                                      >
                                        {pad2(n)}
                                      </button>
                                    ))}
                                  </div>
                                </td>
                                <td className="px-3 py-2 text-xs text-slate-600">
                                  {row.estado ||
                                    (t1Hits.length || t2Hits.length
                                      ? [
                                          t1Hits.length
                                            ? `Tabla 1: ${t1Hits.map(pad2).join(', ')}`
                                            : null,
                                          t2Hits.length
                                            ? `Tabla 2: ${t2Hits.map(pad2).join(', ')}`
                                            : null,
                                        ]
                                          .filter(Boolean)
                                          .join(' · ')
                                      : row.texto || 'Sin cruce destacado')}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <p className="text-slate-600">
                    No encontramos suficientes casos históricos para este número en el período
                    seleccionado.
                  </p>
                )}
              </CardContent>
            </Card>

            <div className="flex flex-wrap gap-2">
              {ctxDate && (
                <Button variant="outline" asChild>
                  <Link href={`/lottery/resultados?date=${ctxDate}`}>Volver al sorteo</Link>
                </Button>
              )}
              {prevStack.length > 0 && (
                <Button
                  variant="outline"
                  onClick={() => {
                    const prev = prevStack[prevStack.length - 1]
                    setPrevStack((s) => s.slice(0, -1))
                    setNumber(prev)
                    void run(prev, '')
                  }}
                >
                  Volver al análisis anterior
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => {
                  setData(null)
                  setNumber('')
                  setCompanion('')
                }}
              >
                Analizar otro número
              </Button>
              <Button variant="outline" asChild>
                <Link href={patternHref}>Consultar comportamiento histórico</Link>
              </Button>
              <Button className="bg-blue-600 hover:bg-blue-700" asChild>
                <Link href={chatHref}>Explicar con Chat inteligente</Link>
              </Button>
            </div>

            {isAdmin && (
              <details className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
                <summary className="cursor-pointer font-medium text-slate-800">
                  Detalle técnico del análisis (solo administración)
                </summary>
                <pre className="mt-3 max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-700">
                  {JSON.stringify(data, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ) : null}
      </div>
    </AppShell>
  )
}
