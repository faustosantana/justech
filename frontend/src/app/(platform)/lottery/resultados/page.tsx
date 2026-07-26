'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken, getUserRole } from '@/lib/auth'
import { canAccessLotteryModule, DISCLAIMER } from '@/lib/lottery'

type Row = {
  draw_id: string
  lottery: string
  lottery_slug: string
  country?: string | null
  date?: string | null
  primera?: string | null
  segunda?: string | null
  tercera?: string | null
  hora?: string | null
  estado?: string
  origen?: string
}

export default function ResultadosPage() {
  const router = useRouter()
  const [rows, setRows] = useState<Row[]>([])
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [pending, setPending] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [date, setDate] = useState('')
  const [lottery, setLottery] = useState('')
  const [country, setCountry] = useState('')
  const [number, setNumber] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryModule(getUserRole())) {
      setError('Sin permiso')
      return
    }
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (date) params.date = date
      if (lottery) params.lottery = lottery
      if (country) params.country = country
      if (number) params.number = number
      const [list, sync, pend] = await Promise.all([
        apiClient.getLotteryResultados(params),
        apiClient.getLotteryResultadosSyncStatus(),
        apiClient.getLotteryResultadosPending(date || undefined),
      ])
      setRows((list.items || []) as Row[])
      setStatus(sync)
      setPending(pend)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar Resultados')
    }
  }, [router, date, lottery, country, number])

  useEffect(() => {
    void load()
  }, [load])

  const triggerSync = async () => {
    setBusy(true)
    try {
      await apiClient.triggerLotteryResultadosSync()
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sync no disponible')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Resultados</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Centro de datos sobre la base oficial (`lottery_draws`). Reutiliza el sync existente —
              no hay segundo scraper. {DISCLAIMER}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void load()}>
              Actualizar vista
            </Button>
            <Button disabled={busy} onClick={() => void triggerSync()}>
              {busy ? 'Sincronizando…' : 'Reprocesar / sync'}
            </Button>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <section className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Última actualización" value={String(status?.last_update ?? '—')} />
          <Stat label="Próxima" value={String(status?.next_update ?? '—')} />
          <Stat label="Estado" value={String(status?.state ?? '—')} />
          <Stat
            label="Sorteos en base"
            value={String(status?.draws_count ?? '—')}
          />
          <Stat label="Última fecha" value={String(status?.last_draw_date ?? '—')} />
          <Stat
            label="Nuevos (último run)"
            value={String((status?.last_run as Record<string, unknown> | undefined)?.records_inserted ?? '—')}
          />
          <Stat
            label="Duplicados/unchanged"
            value={String((status?.last_run as Record<string, unknown> | undefined)?.records_unchanged ?? '—')}
          />
          <Stat
            label="Errores último run"
            value={String((status?.last_run as Record<string, unknown> | undefined)?.errors ?? '—')}
          />
        </section>

        {pending && (
          <p className="text-sm text-muted-foreground">
            Pendientes {(pending as { date?: string }).date}:{' '}
            {(pending as { pending_count?: number }).pending_count ?? 0} loterías sin sorteo.{' '}
            <Link className="underline" href="/lottery/admin/sync">
              Ver sync admin
            </Link>
          </p>
        )}

        <section className="flex flex-wrap gap-2 rounded-lg border bg-card p-4">
          <input
            className="rounded border px-2 py-1 text-sm"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="lotería (slug)"
            value={lottery}
            onChange={(e) => setLottery(e.target.value)}
          />
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="país (DO/US)"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
          />
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="número"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
          />
          <Button variant="secondary" onClick={() => void load()}>
            Filtrar
          </Button>
        </section>

        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50">
              <tr>
                {['Lotería', 'Fecha', 'Primera', 'Segunda', 'Tercera', 'Hora', 'Estado', 'Origen', 'Histórico'].map(
                  (h) => (
                    <th key={h} className="px-3 py-2 font-medium">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.draw_id} className="border-t">
                  <td className="px-3 py-2">{r.lottery}</td>
                  <td className="px-3 py-2">{r.date}</td>
                  <td className="px-3 py-2 font-mono">{r.primera ?? '—'}</td>
                  <td className="px-3 py-2 font-mono">{r.segunda ?? '—'}</td>
                  <td className="px-3 py-2 font-mono">{r.tercera ?? '—'}</td>
                  <td className="px-3 py-2">{r.hora ?? '—'}</td>
                  <td className="px-3 py-2">{r.estado}</td>
                  <td className="px-3 py-2">{r.origen}</td>
                  <td className="px-3 py-2">
                    <Link className="underline" href={`/lottery/lotteries/${r.lottery_slug}`}>
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td className="px-3 py-6 text-muted-foreground" colSpan={9}>
                    Sin filas para los filtros actuales (¿módulo/DB sin draws?).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 break-all text-sm font-medium">{value}</div>
    </div>
  )
}
