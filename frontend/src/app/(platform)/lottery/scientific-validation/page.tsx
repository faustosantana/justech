'use client'

import { useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api/v1'

export default function ScientificValidationPage() {
  const [dash, setDash] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/scientific/dashboard`)
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text())
        return r.json()
      })
      .then(setDash)
      .catch((e) => setErr(e instanceof Error ? e.message : 'Sin datos Fase 2'))
  }, [])

  const bench = (dash?.benchmark_table as Array<Record<string, unknown>>) || []

  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '2rem',
        fontFamily: 'Georgia, serif',
        background: 'linear-gradient(160deg,#eef3f0,#f7f4ef 50%,#e8eef5)',
        color: '#1c2420',
      }}
    >
      <h1 style={{ fontSize: '2.2rem', marginBottom: 8 }}>Validación Científica NR</h1>
      <p style={{ maxWidth: 720 }}>
        Dashboard de medición del motor existente. Producción no modificada. El fuerte sigue siendo
        decisión determinística (sin ML).
      </p>
      {err && <p style={{ color: '#8b1e1e' }}>{err}</p>}
      {dash && (
        <>
          <section
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))',
              gap: 12,
              marginTop: 24,
            }}
          >
            {[
              ['Análisis', dash.total_analyses],
              ['Exactos D+1', dash.exact_D1],
              ['Exactos D+3', dash.exact_D3],
              ['Exactos D+7', dash.exact_D7],
              ['Match metodológico', dash.methodology_match_rate],
              ['Mejor perfil', dash.best_profile],
              ['Errores', (dash.errors as { n_failures?: number })?.n_failures],
            ].map(([k, v]) => (
              <div
                key={String(k)}
                style={{ background: '#fff', border: '1px solid #d5ddd7', padding: 12, borderRadius: 6 }}
              >
                <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{k}</div>
                <div style={{ fontSize: 22, marginTop: 6 }}>{String(v ?? '—')}</div>
              </div>
            ))}
          </section>
          <h2 style={{ marginTop: 28 }}>Benchmark</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
            <thead>
              <tr>
                {['Variante', 'Match', 'D+1', 'D1-D3', 'D1-D7', 'Fallos'].map((h) => (
                  <th key={h} style={{ border: '1px solid #ccc', padding: 6, textAlign: 'left' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bench.map((b) => (
                <tr key={String(b.variant)}>
                  <td style={td}>{String(b.variant)}</td>
                  <td style={td}>{String(b.methodology_match_rate)}</td>
                  <td style={td}>{String(b['exact_D+1'])}</td>
                  <td style={td}>{String(b.exact_D1_D3)}</td>
                  <td style={td}>{String(b.exact_D1_D7)}</td>
                  <td style={td}>{String(b.failures)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  )
}

const td = { border: '1px solid #ccc', padding: 6 } as const
