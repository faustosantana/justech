'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  CalendarDays,
  MessageSquare,
  Search,
  Sparkles,
  Table2,
  ShieldCheck,
} from 'lucide-react'

import { AppShell } from '@/components/layout/app-shell'
import { LotteryNumberLink } from '@/components/lottery/lottery-number-link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import {
  canAccessLotteryAdmin,
  canAccessLotteryModule,
  DEFAULT_DASHBOARD_CONFIG,
  DISCLAIMER,
  PRODUCT_SEVEN_LOTTERY_NAMES,
  type LotteryDashboardConfig,
  type LotteryPreferences,
} from '@/lib/lottery'

type LotteryCard = {
  lottery_id?: string
  lottery?: string
  date?: string | null
  hora?: string | null
  primera?: string | null
  segunda?: string | null
  tercera?: string | null
  status_label?: string
  is_today?: boolean
  draws?: {
    date?: string | null
    primera?: string | null
    segunda?: string | null
    tercera?: string | null
  }[]
}

type Dash = {
  motor?: Record<string, unknown>
  resultados?: Record<string, unknown>
  ultimo_sorteo?: Record<string, unknown>
  piloto?: Record<string, unknown>
  loterias_recientes?: LotteryCard[]
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

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function applyDashboardConfig(
  cards: LotteryCard[],
  cfg: LotteryDashboardConfig,
): LotteryCard[] {
  const disabled = new Set(cfg.disabled_ids || [])
  let list = cards.filter((c) => c.lottery_id && !disabled.has(String(c.lottery_id)))

  if (cfg.lottery_ids?.length) {
    const byId = new Map(list.map((c) => [String(c.lottery_id), c]))
    const ordered: LotteryCard[] = []
    for (const id of cfg.lottery_ids) {
      const hit = byId.get(id)
      if (hit) {
        ordered.push(hit)
        byId.delete(id)
      }
    }
    ordered.push(...byId.values())
    list = ordered
  } else {
    const norm = (s: string) =>
      s
        .normalize('NFD')
        .replace(/\p{M}/gu, '')
        .toLowerCase()
        .trim()
    const rank = new Map(PRODUCT_SEVEN_LOTTERY_NAMES.map((n, i) => [norm(n), i]))
    list = [...list].sort((a, b) => {
      const ra = rank.get(norm(String(a.lottery || ''))) ?? 99
      const rb = rank.get(norm(String(b.lottery || ''))) ?? 99
      return ra - rb
    })
  }
  return list
}

export default function LotteryHomePage() {
  const router = useRouter()
  const [data, setData] = useState<Dash | null>(null)
  const [prefs, setPrefs] = useState<LotteryPreferences | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(true)
  const isAdmin = canAccessLotteryAdmin(getUserRole())

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError('Sin permiso para Lottery IA.')
      setBusy(false)
      return
    }
    setBusy(true)
    try {
      const [dash, preferences] = await Promise.all([
        apiClient.getLotteryIaDashboard() as Promise<Dash>,
        apiClient.getLotteryPreferences().catch(() => null),
      ])
      setData(dash)
      setPrefs(preferences)
      setError(null)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'No fue posible consultar los resultados. Intente nuevamente.',
      )
    } finally {
      setBusy(false)
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const dashCfg = prefs?.dashboard || DEFAULT_DASHBOARD_CONFIG
  const lotteryCards = useMemo(
    () => applyDashboardConfig(data?.loterias_recientes || [], dashCfg),
    [data?.loterias_recientes, dashCfg],
  )

  const r = data?.resultados || {}
  const last = data?.ultimo_sorteo || {}
  const syncOk = String(r.estado_sync || '').toLowerCase() !== 'error'
  const pending = Number(r.pendientes_sincronizar || 0)
  const today = todayIso()

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="rounded-2xl bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 px-6 py-8 text-white shadow-md">
          <p className="text-sm font-medium text-blue-100">Lottery IA</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Inicio</h1>
          <p className="mt-2 max-w-2xl text-sm text-blue-50">
            Consulte resultados, analice números y revise recomendaciones del motor protegido.
          </p>
          <p className="mt-3 text-xs text-blue-100/90">{DISCLAIMER}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button asChild className="bg-white text-blue-700 hover:bg-blue-50">
              <Link href="/lottery/analizar">Analizar número</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="border-white/40 bg-white/10 text-white hover:bg-white/20"
            >
              <Link href={`/lottery/resultados?date=${today}`}>Ver resultados de hoy</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="border-white/40 bg-white/10 text-white hover:bg-white/20"
            >
              <Link href="/lottery/chat">Abrir Chat inteligente</Link>
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
            <Button size="sm" variant="outline" className="ml-3" onClick={() => void load()}>
              Reintentar
            </Button>
          </div>
        )}

        {busy && !data && <p className="text-sm text-slate-500">Cargando información…</p>}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-blue-100">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-blue-900">
                <ShieldCheck className="h-4 w-4" /> Estado
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p>
                <span className="text-slate-500">Sistema:</span>{' '}
                <span className="font-medium text-emerald-700">Operativo</span>
              </p>
              <p>
                <span className="text-slate-500">Resultados:</span>{' '}
                <span className="font-medium">{syncOk ? 'Actualizados' : 'Revisar sync'}</span>
              </p>
              <p>
                <span className="text-slate-500">Última actualización:</span>{' '}
                <span className="font-medium">{fmtDate(r.ultima_actualizacion || r.ultima_fecha)}</span>
              </p>
              {pending > 0 && (
                <p className="text-amber-700">
                  La sincronización todavía no ha terminado ({pending} pendientes).
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border-blue-100 md:col-span-2 xl:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-blue-900">
                <Sparkles className="h-4 w-4" /> Recomendación
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {Array.isArray(last.prediccion) && last.prediccion.length ? (
                <>
                  <p className="text-xs uppercase text-amber-700">Números destacados</p>
                  <div className="flex flex-wrap gap-2">
                    {(last.prediccion as unknown[]).map((n, i) => (
                      <LotteryNumberLink
                        key={`${n}-${i}`}
                        number={String(n)}
                        size={i === 0 ? 'lg' : 'sm'}
                        className={i === 0 ? undefined : 'bg-amber-500 hover:bg-amber-600'}
                      />
                    ))}
                  </div>
                  <p className="text-slate-600">
                    Estado: {String(last.estado || 'Resultado pendiente')}
                  </p>
                </>
              ) : (
                <p className="text-slate-600">
                  Sin recomendación destacada todavía. Analice un número para comenzar.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-blue-900">Resultados recientes</h2>
              <p className="text-sm text-slate-600">
                Loterías activas con su último sorteo. Pulse un número para analizarlo.
              </p>
            </div>
            {isAdmin && (
              <Button variant="outline" size="sm" asChild>
                <Link href="/lottery/administracion/dashboard">Configurar Dashboard</Link>
              </Button>
            )}
          </div>

          {!lotteryCards.length && !busy ? (
            <p className="text-sm text-slate-500">No hay resultados disponibles por ahora.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {lotteryCards.map((card) => {
                const draws =
                  dashCfg.recent_draws > 1 && card.draws?.length
                    ? card.draws.slice(0, dashCfg.recent_draws)
                    : [
                        {
                          date: card.date,
                          primera: card.primera,
                          segunda: card.segunda,
                          tercera: card.tercera,
                        },
                      ]
                return (
                  <Card key={card.lottery_id || card.lottery} className="border-blue-100">
                    <CardContent className="space-y-3 pt-5">
                      <div>
                        <p className="font-semibold text-slate-900">{card.lottery || '—'}</p>
                        <p className="text-sm text-slate-500">{fmtDate(draws[0]?.date || card.date)}</p>
                        <p
                          className={`mt-1 text-xs font-medium ${
                            card.is_today ? 'text-emerald-700' : 'text-amber-700'
                          }`}
                        >
                          {card.status_label || 'Último disponible'}
                        </p>
                      </div>
                      {draws.map((draw, idx) => (
                        <div key={`${card.lottery_id}-${draw.date}-${idx}`} className="space-y-1">
                          {idx > 0 && (
                            <p className="text-xs text-slate-500">{fmtDate(draw.date)}</p>
                          )}
                          <div className="flex flex-wrap items-center gap-2">
                            {dashCfg.show_primera !== false && (
                              <LotteryNumberLink
                                number={String(draw.primera || '')}
                                size="lg"
                                lottery={card.lottery}
                                date={draw.date}
                                position="primera"
                              />
                            )}
                            {dashCfg.show_segunda !== false && (
                              <LotteryNumberLink
                                number={String(draw.segunda || '')}
                                size="lg"
                                lottery={card.lottery}
                                date={draw.date}
                                position="segunda"
                                className="bg-sky-600 hover:bg-sky-700"
                              />
                            )}
                            {dashCfg.show_tercera !== false && (
                              <LotteryNumberLink
                                number={String(draw.tercera || '')}
                                size="lg"
                                lottery={card.lottery}
                                date={draw.date}
                                position="tercera"
                                className="bg-indigo-600 hover:bg-indigo-700"
                              />
                            )}
                            {!draw.primera && !draw.segunda && !draw.tercera && (
                              <span className="text-sm text-slate-500">Sin resultados</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </section>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { href: '/lottery/analizar', label: 'Analizar número', icon: Search },
            { href: '/lottery/resultados', label: 'Resultados e histórico', icon: CalendarDays },
            { href: '/lottery/patrones', label: 'Patrones y tablas', icon: Table2 },
            { href: '/lottery/chat', label: 'Chat inteligente', icon: MessageSquare },
          ].map((item) => (
            <Link key={item.href} href={item.href}>
              <Card className="border-blue-100 transition hover:border-blue-300 hover:shadow-sm">
                <CardContent className="flex items-center gap-3 py-5">
                  <item.icon className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-slate-900">{item.label}</span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {isAdmin && (
          <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm text-blue-900">
            Acceso administrativo disponible.{' '}
            <Link href="/lottery/administracion" className="font-semibold underline">
              Abrir Administración
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  )
}
