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

type Analysis = {
  primary_signal?: {
    number?: number
    reason?: string
    classification?: string
    analytical_confidence?: number
    score?: number
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
  explanation?: { summary?: string; body?: Record<string, unknown> }
  observed_numbers?: number[]
  derivations?: { path?: number[]; via?: string; numbers?: number[] }[]
  graph?: {
    nodes?: { id?: string; number?: number; role?: string }[]
    edges?: { source?: number; target?: number; relation?: string; type?: string }[]
  }
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
            date: ctxDate || undefined,
            positions: ctxPosition ? [ctxPosition] : undefined,
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
    [number, companion, router, ctxDate, ctxPosition, loadTables, loadHistory, loadDrawContext],
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

  const analyzeNumber = (n: number) => {
    if (observed) setPrevStack((s) => [...s, String(observed)])
    setNumber(String(n))
    setCompanion('')
    const params = new URLSearchParams()
    params.set('number', String(n))
    params.set('auto', '1')
    router.push(`/lottery/analizar?${params.toString()}`)
    void run(String(n), '')
  }

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
                <CardTitle className="text-base text-blue-900">Cruce de relaciones</CardTitle>
              </CardHeader>
              <CardContent className="text-sm leading-relaxed text-slate-700">
                {narrative ||
                  'El motor no encontró un cruce suficiente entre Tabla 1 y Tabla 2 para este número.'}
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
