'use client'

import { useCallback, useEffect, useState } from 'react'
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
import { canAccessLotteryAdmin, canAccessLotteryModule, DISCLAIMER } from '@/lib/lottery'

type Dash = {
  motor?: Record<string, unknown>
  resultados?: Record<string, unknown>
  ultimo_sorteo?: Record<string, unknown>
  piloto?: Record<string, unknown>
}

function fmtDate(v: unknown): string {
  if (!v) return '—'
  try {
    return new Date(String(v)).toLocaleDateString('es-DO', { dateStyle: 'medium' })
  } catch {
    return String(v)
  }
}

export default function LotteryHomePage() {
  const router = useRouter()
  const [data, setData] = useState<Dash | null>(null)
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
      const dash = (await apiClient.getLotteryIaDashboard()) as Dash
      setData(dash)
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

  const r = data?.resultados || {}
  const last = data?.ultimo_sorteo || {}
  const resultado = (last.resultado || {}) as Record<string, unknown>
  const syncOk = String(r.estado_sync || '').toLowerCase() !== 'error'
  const pending = Number(r.pendientes_sincronizar || 0)

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
            <Button asChild variant="outline" className="border-white/40 bg-white/10 text-white hover:bg-white/20">
              <Link href="/lottery/resultados">Ver resultados de hoy</Link>
            </Button>
            <Button asChild variant="outline" className="border-white/40 bg-white/10 text-white hover:bg-white/20">
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
                <p className="text-amber-700">La sincronización todavía no ha terminado ({pending} pendientes).</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-blue-100 md:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-blue-900">
                <CalendarDays className="h-4 w-4" /> Resultados recientes
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-slate-500">Lotería:</span>{' '}
                <span className="font-medium">{String(last.loteria || '—')}</span>
              </p>
              <p>
                <span className="text-slate-500">Fecha:</span>{' '}
                <span className="font-medium">{fmtDate(last.fecha)}</span>
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {resultado.primera ? (
                  <>
                    <LotteryNumberLink number={String(resultado.primera)} />
                    <LotteryNumberLink number={String(resultado.segunda || '')} />
                    <LotteryNumberLink number={String(resultado.tercera || '')} />
                  </>
                ) : (
                  <span className="text-slate-500">No hay resultados para este período.</span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Total sorteos: {String(r.total_sorteos ?? '—')} · Último disponible: {fmtDate(r.ultima_fecha)}
              </p>
            </CardContent>
          </Card>

          <Card className="border-blue-100">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-blue-900">
                <Sparkles className="h-4 w-4" /> Recomendación
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {Array.isArray(last.prediccion) && last.prediccion.length ? (
                <>
                  <p className="text-xs uppercase text-amber-700">Número fuerte / alternativas</p>
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
                <p className="text-slate-600">Sin recomendación destacada todavía. Analice un número para comenzar.</p>
              )}
            </CardContent>
          </Card>
        </div>

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
