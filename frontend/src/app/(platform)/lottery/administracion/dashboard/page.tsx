'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import {
  canAccessLotteryAdmin,
  DEFAULT_DASHBOARD_CONFIG,
  DISCLAIMER,
  PRODUCT_SEVEN_LOTTERY_NAMES,
  type LotteryDashboardConfig,
} from '@/lib/lottery'

type Lot = { id: string; name: string }

function sortByProductSeven(lots: Lot[]): Lot[] {
  const rank = new Map(PRODUCT_SEVEN_LOTTERY_NAMES.map((n, i) => [n.toLowerCase(), i]))
  return [...lots].sort((a, b) => {
    const ra = rank.get(a.name.toLowerCase()) ?? 99
    const rb = rank.get(b.name.toLowerCase()) ?? 99
    return ra - rb || a.name.localeCompare(b.name)
  })
}

export default function DashboardConfigPage() {
  const router = useRouter()
  const [lots, setLots] = useState<Lot[]>([])
  const [cfg, setCfg] = useState<LotteryDashboardConfig>(DEFAULT_DASHBOARD_CONFIG)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryAdmin(getUserRole())) {
      router.replace('/lottery')
      return
    }
    try {
      const [featured, prefs] = await Promise.all([
        apiClient.getLotteryResultadosLotteries(),
        apiClient.getLotteryPreferences(),
      ])
      const items = sortByProductSeven(
        ((featured.items || []) as Lot[]).map((l) => ({ id: l.id, name: l.name })),
      )
      setLots(items)
      const dash = prefs.dashboard || DEFAULT_DASHBOARD_CONFIG
      setCfg({
        ...DEFAULT_DASHBOARD_CONFIG,
        ...dash,
        lottery_ids: dash.lottery_ids?.length ? dash.lottery_ids : items.map((l) => l.id),
        disabled_ids: dash.disabled_ids || [],
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar la configuración')
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const move = (id: string, dir: -1 | 1) => {
    setCfg((c) => {
      const ids = [...(c.lottery_ids.length ? c.lottery_ids : lots.map((l) => l.id))]
      const i = ids.indexOf(id)
      if (i < 0) return c
      const j = i + dir
      if (j < 0 || j >= ids.length) return c
      ;[ids[i], ids[j]] = [ids[j], ids[i]]
      return { ...c, lottery_ids: ids }
    })
  }

  const toggleEnabled = (id: string) => {
    setCfg((c) => {
      const disabled = new Set(c.disabled_ids || [])
      if (disabled.has(id)) disabled.delete(id)
      else disabled.add(id)
      return { ...c, disabled_ids: Array.from(disabled) }
    })
  }

  const save = async () => {
    setBusy(true)
    setMsg(null)
    setError(null)
    try {
      await apiClient.patchLotteryPreferences({ dashboard: cfg })
      setMsg('Configuración guardada para su usuario.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar')
    } finally {
      setBusy(false)
    }
  }

  const restore = async () => {
    const next: LotteryDashboardConfig = {
      ...DEFAULT_DASHBOARD_CONFIG,
      lottery_ids: lots.map((l) => l.id),
      disabled_ids: [],
    }
    setCfg(next)
    setBusy(true)
    setError(null)
    try {
      await apiClient.patchLotteryPreferences({ dashboard: next })
      setMsg('Configuración predeterminada restaurada.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo restaurar')
    } finally {
      setBusy(false)
    }
  }

  const ordered = (cfg.lottery_ids.length ? cfg.lottery_ids : lots.map((l) => l.id))
    .map((id) => lots.find((l) => l.id === id))
    .filter(Boolean) as Lot[]
  for (const l of lots) {
    if (!ordered.find((x) => x.id === l.id)) ordered.push(l)
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <div>
          <p className="text-sm font-medium text-blue-700">Administración</p>
          <h1 className="text-2xl font-semibold text-slate-900">Configuración del Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Elija qué loterías aparecen en el Inicio, su orden y cuántos sorteos mostrar.{' '}
            {DISCLAIMER}
          </p>
        </div>

        <Card className="border-blue-100">
          <CardHeader>
            <CardTitle className="text-base text-blue-900">Loterías visibles</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {ordered.map((lot) => {
              const enabled = !(cfg.disabled_ids || []).includes(lot.id)
              return (
                <div
                  key={lot.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-blue-50 bg-blue-50/30 px-3 py-2"
                >
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={() => toggleEnabled(lot.id)}
                    />
                    <span className={enabled ? 'font-medium text-slate-900' : 'text-slate-400'}>
                      {lot.name}
                    </span>
                  </label>
                  <div className="flex gap-1">
                    <Button type="button" size="sm" variant="outline" onClick={() => move(lot.id, -1)}>
                      Subir
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => move(lot.id, 1)}>
                      Bajar
                    </Button>
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        <Card className="border-blue-100">
          <CardHeader>
            <CardTitle className="text-base text-blue-900">Opciones de visualización</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4 text-sm">
            <label>
              Sorteos recientes por lotería
              <Input
                className="mt-1 w-24"
                type="number"
                min={1}
                max={7}
                value={cfg.recent_draws}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    recent_draws: Math.max(1, Math.min(7, Number(e.target.value) || 1)),
                  }))
                }
              />
            </label>
            <label className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                checked={cfg.show_primera}
                onChange={(e) => setCfg((c) => ({ ...c, show_primera: e.target.checked }))}
              />
              Mostrar primera
            </label>
            <label className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                checked={cfg.show_segunda}
                onChange={(e) => setCfg((c) => ({ ...c, show_segunda: e.target.checked }))}
              />
              Mostrar segunda
            </label>
            <label className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                checked={cfg.show_tercera}
                onChange={(e) => setCfg((c) => ({ ...c, show_tercera: e.target.checked }))}
              />
              Mostrar tercera
            </label>
          </CardContent>
        </Card>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        {msg && (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {msg}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button className="bg-blue-600 hover:bg-blue-700" disabled={busy} onClick={() => void save()}>
            {busy ? 'Guardando…' : 'Guardar'}
          </Button>
          <Button variant="outline" disabled={busy} onClick={() => void restore()}>
            Restaurar predeterminada
          </Button>
          <Button variant="outline" asChild>
            <Link href="/lottery">Ver Inicio</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/lottery/administracion">Volver a Administración</Link>
          </Button>
        </div>
      </div>
    </AppShell>
  )
}
