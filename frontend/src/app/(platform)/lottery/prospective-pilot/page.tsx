'use client'

import { useCallback, useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE || '/api/v1'

export default function ProspectivePilotPage() {
  const [pilots, setPilots] = useState<Record<string, unknown>[]>([])
  const [preds, setPreds] = useState<Record<string, unknown>[]>([])
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null)
  const [audit, setAudit] = useState<unknown[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [numbers, setNumbers] = useState('35,14')
  const [date, setDate] = useState('')

  const refresh = useCallback(() => {
    Promise.all([
      fetch(`${API}/pilot/configurations`).then((r) => r.json()),
      fetch(`${API}/prospective-validation/predictions`).then((r) => r.json()),
      fetch(`${API}/prospective-validation/metrics`).then((r) => r.json()),
      fetch(`${API}/prospective-validation/comparison`).then((r) => r.json()),
    ])
      .then(([p, pr, m, c]) => {
        setPilots(p.configurations || [])
        setPreds(pr.predictions || [])
        setMetrics(m)
        setComparison(c)
      })
      .catch((e) => setErr(e instanceof Error ? e.message : 'error'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function createPilot() {
    await fetch(`${API}/pilot/configurations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pilot_name: 'DEV/UAT Prospective Pilot',
        ranking_profile: 'socio',
        tiebreak_profile: 'TIEBREAK_PROFILE_SOCIO_V1',
        positions: ['first'],
        status: 'DRAFT',
      }),
    })
    refresh()
  }

  async function activate(id: string) {
    await fetch(`${API}/pilot/configurations/${id}/activate`, { method: 'POST' })
    refresh()
  }

  async function pause(id: string) {
    await fetch(`${API}/pilot/configurations/${id}/pause`, { method: 'POST' })
    refresh()
  }

  async function runDaily() {
    const nums = numbers
      .split(',')
      .map((x) => parseInt(x.trim(), 10))
      .filter((n) => !Number.isNaN(n))
    await fetch(`${API}/prospective-validation/run-daily`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        numbers: nums,
        analysis_date: date || undefined,
        auto_lock: false,
        include_shadow: true,
      }),
    })
    refresh()
  }

  async function lock(id: string) {
    await fetch(`${API}/prospective-validation/predictions/${id}/prepare-lock`, { method: 'POST' })
    await fetch(`${API}/prospective-validation/predictions/${id}/lock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ locked_by: 'uat-ui' }),
    })
    refresh()
  }

  async function showAudit(id: string) {
    setSelected(id)
    const r = await fetch(`${API}/prospective-validation/predictions/${id}/audit-log`)
    const j = await r.json()
    setAudit(j.audit_log || [])
  }

  const locked = preds.filter((p) =>
    ['LOCKED', 'AWAITING_RESULTS', 'EVALUATED'].includes(String(p.status)),
  )

  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '2rem',
        fontFamily: 'Georgia, serif',
        background: 'linear-gradient(160deg,#eef3f0,#f8f5ef)',
        color: '#1b2420',
      }}
    >
      <h1>Piloto Prospectivo DEV/UAT</h1>
      <p style={{ maxWidth: 760 }}>
        Persistencia real, bloqueo con hash, multi-fuerte operativo, perfiles sombra y evaluación D+1…D+7.
        Producción no modificada.
      </p>
      {err && <p style={{ color: '#8b1e1e' }}>{err}</p>}

      <section style={card}>
        <h2>Configuración</h2>
        <button style={btn} onClick={createPilot}>
          Crear piloto
        </button>
        <ul>
          {pilots.map((p) => (
            <li key={String(p.id)} style={{ marginTop: 8 }}>
              {String(p.pilot_name)} — {String(p.status)} — {String(p.ranking_profile)} /{' '}
              {String(p.tiebreak_profile)}{' '}
              <button style={btn} onClick={() => activate(String(p.id))}>
                Activar
              </button>{' '}
              <button style={btn} onClick={() => pause(String(p.id))}>
                Pausar
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section style={card}>
        <h2>Predicciones del día</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            value={numbers}
            onChange={(e) => setNumbers(e.target.value)}
            placeholder="números ej. 35,14"
            style={input}
          />
          <input
            value={date}
            onChange={(e) => setDate(e.target.value)}
            placeholder="fecha análisis YYYY-MM-DD"
            style={input}
          />
          <button style={btn} onClick={runDaily}>
            Ejecutar predicción
          </button>
        </div>
        <table style={table}>
          <thead>
            <tr>
              {['ID', 'Estado', 'Primary/Multi', 'Score', 'Acción'].map((h) => (
                <th key={h} style={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preds.map((p) => {
              const primary = p.primary_signal as Record<string, unknown> | undefined
              const multi = (p.multi_strong_candidates as number[]) || []
              return (
                <tr key={String(p.prediction_id)}>
                  <td style={td}>{String(p.prediction_id).slice(0, 12)}</td>
                  <td style={td}>{String(p.status)}</td>
                  <td style={td}>
                    {multi.length
                      ? `MULTI ${multi.join(',')}`
                      : String(primary?.number ?? '—')}
                  </td>
                  <td style={td}>{String(primary?.score ?? '—')}</td>
                  <td style={td}>
                    {p.status === 'DRAFT' || p.status === 'READY_TO_LOCK' ? (
                      <button style={btn} onClick={() => lock(String(p.prediction_id))}>
                        Bloquear
                      </button>
                    ) : (
                      <button style={btn} onClick={() => showAudit(String(p.prediction_id))}>
                        Auditoría
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      <section style={card}>
        <h2>Predicciones bloqueadas</h2>
        <ul>
          {locked.map((p) => (
            <li key={String(p.prediction_id)}>
              {String(p.prediction_id)} — hash {String(p.prediction_hash || '').slice(0, 16)}… —{' '}
              {String(p.engine_version)} — {String(p.tiebreak_profile)}
            </li>
          ))}
        </ul>
      </section>

      <section style={card}>
        <h2>Métricas</h2>
        <pre style={{ fontSize: 12, overflow: 'auto' }}>{JSON.stringify(metrics, null, 2)}</pre>
      </section>

      <section style={card}>
        <h2>Comparación sombra</h2>
        <pre style={{ fontSize: 12, overflow: 'auto' }}>{JSON.stringify(comparison, null, 2)}</pre>
      </section>

      {selected && (
        <section style={card}>
          <h2>Auditoría {selected}</h2>
          <pre style={{ fontSize: 12, overflow: 'auto' }}>{JSON.stringify(audit, null, 2)}</pre>
        </section>
      )}
    </main>
  )
}

const card = {
  background: '#fff',
  border: '1px solid #d5ddd7',
  padding: 16,
  marginTop: 20,
} as const
const btn = {
  border: '1px solid #8a9a90',
  background: '#f3f7f4',
  padding: '6px 10px',
  cursor: 'pointer',
} as const
const input = { border: '1px solid #ccc', padding: 6, minWidth: 180 } as const
const table = { width: '100%', borderCollapse: 'collapse' as const, marginTop: 12 }
const th = { border: '1px solid #ccc', padding: 6, textAlign: 'left' as const }
const td = { border: '1px solid #ccc', padding: 6 }
