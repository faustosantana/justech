'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE || '/api/v1'

type ErrCase = Record<string, unknown>

export default function TiebreakValidationPage() {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)
  const [errors, setErrors] = useState<ErrCase[]>([])
  const [selected, setSelected] = useState<ErrCase | null>(null)
  const [prospective, setProspective] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch(`${API}/tiebreak/summary`).then(async (r) => {
        if (!r.ok) throw new Error(await r.text())
        return r.json()
      }),
      fetch(`${API}/tiebreak/errors`).then(async (r) => {
        if (!r.ok) return { cases: [] }
        return r.json()
      }),
      fetch(`${API}/prospective-validation/metrics`).then(async (r) => {
        if (!r.ok) return null
        return r.json()
      }),
    ])
      .then(([s, e, p]) => {
        setSummary(s)
        setErrors(e.cases || [])
        setProspective(p)
      })
      .catch((e) => setErr(e instanceof Error ? e.message : 'Sin artefactos'))
  }, [])

  const o14 = (summary?.original_14 || {}) as Record<string, Record<string, number>>
  const test = (summary?.test_socio_multi || summary?.test_engine_integrated || {}) as Record<
    string,
    number
  >
  const val = (summary?.validation_socio_multi || summary?.validation_selected || {}) as Record<
    string,
    number
  >

  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '2rem',
        fontFamily: 'Georgia, serif',
        background: 'linear-gradient(150deg,#eef2f0,#f7f4ef)',
        color: '#1c2420',
      }}
    >
      <h1>Validación de Desempate Multi-Fuerte</h1>
      <p style={{ maxWidth: 720 }}>
        Fase 3 — ordenar candidatos ya descubiertos. Umbral práctico 0 (empates reales). Producción no
        modificada.
      </p>
      {err && <p style={{ color: '#8b1e1e' }}>{err}</p>}
      {summary && (
        <section
          style={{
            display: 'grid',
            gap: 12,
            gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))',
          }}
        >
          {[
            ['Regla', summary.selected_operational_rule],
            ['Val top-1', val.top1_rate],
            ['Val top-2', val.top2_rate],
            ['Test top-1 multi', test.top1_rate],
            ['Test top-2', test.top2_rate],
            ['Multi-fuerte rate', test.multi_fuerte_rate],
            ['14 baseline top1', o14.baseline?.top1_rate],
            ['14 socio+multi top2', o14.socio_multi?.top2_rate],
            ['Prospectivas', prospective ? JSON.stringify(prospective) : '—'],
          ].map(([k, v]) => (
            <div
              key={String(k)}
              style={{ background: '#fff', border: '1px solid #d5ddd7', padding: 12 }}
            >
              <div style={{ fontSize: 12, textTransform: 'uppercase' }}>{k}</div>
              <div style={{ marginTop: 6, fontSize: 18, wordBreak: 'break-word' }}>
                {String(v ?? '—')}
              </div>
            </div>
          ))}
        </section>
      )}
      <h2 style={{ marginTop: 28 }}>14 errores auditados</h2>
      <p style={{ fontSize: 14 }}>Clic en una fila para ver comparación hist vs elegido.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
        <thead>
          <tr>
            {['Fecha', 'Obs', 'Elegido', 'Histórico', 'Empate real', 'Gap'].map((h) => (
              <th key={h} style={{ border: '1px solid #ccc', padding: 6, textAlign: 'left' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {errors.map((c) => (
            <tr
              key={String(c.scenario_id)}
              onClick={() => setSelected(c)}
              style={{ cursor: 'pointer', background: selected?.scenario_id === c.scenario_id ? '#e8efe9' : undefined }}
            >
              <td style={td}>{String(c.date)}</td>
              <td style={td}>{JSON.stringify(c.observed_generator_first || c.observed_numbers)}</td>
              <td style={td}>{String(c.chosen_by_motor_phase2)}</td>
              <td style={td}>{String(c.historical_fuerte)}</td>
              <td style={td}>{String(c.real_tie)}</td>
              <td style={td}>{String(c.score_gap)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <section style={{ marginTop: 24, background: '#fff', border: '1px solid #d5ddd7', padding: 16 }}>
          <h3>Caso {String(selected.scenario_id)}</h3>
          <pre style={{ overflow: 'auto', fontSize: 12, maxHeight: 420 }}>
            {JSON.stringify(
              {
                chosen_detail: selected.chosen_detail,
                historical_detail: selected.historical_detail,
                alternatives: selected.alternatives,
                lotteries: selected.lotteries,
                positions: selected.positions,
              },
              null,
              2,
            )}
          </pre>
        </section>
      )}
    </main>
  )
}

const td = { border: '1px solid #ccc', padding: 6 } as const
