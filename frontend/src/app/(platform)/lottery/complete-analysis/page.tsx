'use client'

import { useMemo, useState } from 'react'

type Ranked = {
  number: number
  classification: string
  total_score: number
  analytical_confidence: number
  classification_reason?: string
}

type Analysis = {
  analysis_id: string
  observed_numbers: number[]
  primary_signal: {
    number: number
    classification: string
    analytical_confidence: number
    reason?: string
  } | null
  alternatives: { number: number; classification: string; score: number }[]
  ranked_candidates: Ranked[]
  evidence_summary: Record<string, unknown>
  explanation?: { summary?: string; disclaimer?: string }
  graph?: { node_count?: number; edge_count?: number; complete?: boolean }
  experimental?: boolean
  limitations?: string[]
  stages_completed?: string[]
}

type ChatResp = {
  message: string
  primary_signal?: Analysis['primary_signal']
  alternatives?: Analysis['alternatives']
  conversation_id?: string
  disclaimer?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api/v1'

export default function CompleteAnalysisPage() {
  const [numbers, setNumbers] = useState('35, 14')
  const [date, setDate] = useState('2026-06-23')
  const [mode, setMode] = useState('manual_reconstruido')
  const [depth, setDepth] = useState(2)
  const [level, setLevel] = useState('analitico')
  const [tech, setTech] = useState(false)
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [chat, setChat] = useState('')
  const [chatLog, setChatLog] = useState<{ role: string; text: string }[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>()

  const parsedNumbers = useMemo(
    () =>
      numbers
        .split(/[,\s]+/)
        .map((x) => x.trim())
        .filter(Boolean)
        .map((x) => Number(x))
        .filter((n) => n >= 1 && n <= 100),
    [numbers]
  )

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/analysis/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date,
          numbers: parsedNumbers,
          positions: ['first'],
          mode,
          derivation_depth: depth,
          explanation_level: level,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = (await res.json()) as Analysis
      setAnalysis(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al analizar')
    } finally {
      setLoading(false)
    }
  }

  async function sendChat() {
    if (!chat.trim()) return
    const msg = chat.trim()
    setChat('')
    setChatLog((l) => [...l, { role: 'user', text: msg }])
    try {
      const res = await fetch(`${API_BASE}/j11a/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          conversation_id: conversationId,
          date,
          mode,
          use_llm: false,
        }),
      })
      const data = (await res.json()) as ChatResp
      if (data.conversation_id) setConversationId(data.conversation_id)
      setChatLog((l) => [...l, { role: 'j11a', text: data.message }])
    } catch (e) {
      setChatLog((l) => [
        ...l,
        {
          role: 'j11a',
          text:
            e instanceof Error
              ? e.message
              : 'No fue posible calcular el análisis. No generaré una predicción sin resultados verificables.',
        },
      ])
    }
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '2rem',
        fontFamily: 'Georgia, "Times New Roman", serif',
        background:
          'radial-gradient(circle at top left, #e8f0ea 0%, #f7f4ef 45%, #eef2f6 100%)',
        color: '#1c2420',
      }}
    >
      <header style={{ maxWidth: 1100, margin: '0 auto 2rem' }}>
        <p style={{ letterSpacing: '0.12em', textTransform: 'uppercase', fontSize: 12, margin: 0 }}>
          Lottery IA · Motor de Relaciones Numéricas
        </p>
        <h1 style={{ fontSize: '2.4rem', margin: '0.4rem 0' }}>Análisis Completo + J-11A</h1>
        <p style={{ maxWidth: 640, lineHeight: 1.5, margin: 0 }}>
          El motor calcula. J-11A explica. Las predicciones son experimentales basadas en relaciones —
          no son probabilidad de ganar ni recomendación de apuesta.
        </p>
      </header>

      <section
        style={{
          maxWidth: 1100,
          margin: '0 auto',
          display: 'grid',
          gap: '1.25rem',
          gridTemplateColumns: 'minmax(280px, 360px) 1fr',
        }}
      >
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <label>
            Fecha
            <input value={date} onChange={(e) => setDate(e.target.value)} style={inputStyle} />
          </label>
          <label>
            Números observados
            <input value={numbers} onChange={(e) => setNumbers(e.target.value)} style={inputStyle} />
          </label>
          <label>
            Modo / perfil
            <select value={mode} onChange={(e) => setMode(e.target.value)} style={inputStyle}>
              <option value="manual_reconstruido">Manual reconstruido</option>
              <option value="strict">Estricto</option>
              <option value="amplio">Amplio</option>
              <option value="experimental">Experimental</option>
            </select>
          </label>
          <label>
            Profundidad de derivación
            <input
              type="number"
              min={0}
              max={2}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
          <label>
            Nivel de explicación
            <select value={level} onChange={(e) => setLevel(e.target.value)} style={inputStyle}>
              <option value="ejecutivo">Ejecutivo</option>
              <option value="analitico">Analítico</option>
              <option value="tecnico">Técnico</option>
            </select>
          </label>
          <button onClick={runAnalysis} disabled={loading || parsedNumbers.length < 1} style={btnStyle}>
            {loading ? 'Analizando…' : 'Ejecutar análisis completo'}
          </button>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 14 }}>
            <input type="checkbox" checked={tech} onChange={(e) => setTech(e.target.checked)} />
            Vista técnica (desarrollador)
          </label>
          {error && <p style={{ color: '#8b1e1e' }}>{error}</p>}
        </div>

        <div style={{ display: 'grid', gap: '1rem' }}>
          {analysis && (
            <article style={cardStyle}>
              <h2 style={{ marginTop: 0 }}>Resultados</h2>
              {analysis.primary_signal ? (
                <p style={{ fontSize: '1.35rem', marginBottom: 8 }}>
                  Señal principal: <strong>{analysis.primary_signal.number}</strong>{' '}
                  <span>({analysis.primary_signal.classification})</span>
                  <br />
                  <span style={{ fontSize: '0.95rem' }}>
                    Respaldo estructural: {analysis.primary_signal.analytical_confidence}/100
                  </span>
                </p>
              ) : (
                <p>Sin candidato con evidencia suficiente.</p>
              )}
              <p style={{ lineHeight: 1.5 }}>{analysis.explanation?.summary}</p>
              <p style={{ fontSize: 13, opacity: 0.8 }}>{analysis.explanation?.disclaimer}</p>
              {analysis.alternatives?.length > 0 && (
                <div>
                  <h3>Alternativas</h3>
                  <ul>
                    {analysis.alternatives.map((a) => (
                      <li key={a.number}>
                        {a.number} · {a.classification} · score {a.score}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div>
                <h3>Evidencia</h3>
                <pre style={preStyle}>{JSON.stringify(analysis.evidence_summary, null, 2)}</pre>
              </div>
              <div>
                <h3>Grafo</h3>
                <p>
                  Completo: {String(analysis.graph?.complete)} · nodos {analysis.graph?.node_count} ·
                  aristas {analysis.graph?.edge_count}
                </p>
              </div>
              {tech && (
                <div>
                  <h3>Vista técnica</h3>
                  <pre style={preStyle}>
                    {JSON.stringify(
                      {
                        analysis_id: analysis.analysis_id,
                        stages: analysis.stages_completed,
                        ranked: analysis.ranked_candidates?.slice(0, 8),
                        limitations: analysis.limitations,
                      },
                      null,
                      2
                    )}
                  </pre>
                </div>
              )}
            </article>
          )}

          <article style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Copiloto J-11A</h2>
            <div style={{ display: 'grid', gap: 8, marginBottom: 12, maxHeight: 280, overflow: 'auto' }}>
              {chatLog.map((m, i) => (
                <div key={i} style={{ fontSize: 14 }}>
                  <strong>{m.role === 'user' ? 'Tú' : 'J-11A'}:</strong> {m.text}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={chat}
                onChange={(e) => setChat(e.target.value)}
                placeholder='Ej: Analiza 35 y 14 / ¿Por qué quedó fuerte el 54?'
                style={{ ...inputStyle, margin: 0, flex: 1 }}
                onKeyDown={(e) => e.key === 'Enter' && sendChat()}
              />
              <button onClick={sendChat} style={btnStyle}>
                Enviar
              </button>
            </div>
          </article>
        </div>
      </section>
    </main>
  )
}

const inputStyle = {
  display: 'block',
  width: '100%',
  marginTop: 6,
  padding: '0.65rem 0.75rem',
  border: '1px solid #b7c4bc',
  borderRadius: 4,
  background: '#fff',
  font: 'inherit',
} as const

const btnStyle = {
  padding: '0.75rem 1rem',
  border: 'none',
  borderRadius: 4,
  background: '#1f4d3a',
  color: '#f4faf6',
  font: 'inherit',
  cursor: 'pointer',
} as const

const cardStyle = {
  background: 'rgba(255,255,255,0.72)',
  border: '1px solid #d5ddd7',
  padding: '1.25rem',
  borderRadius: 6,
} as const

const preStyle = {
  background: '#17201c',
  color: '#d7ece0',
  padding: 12,
  borderRadius: 4,
  overflow: 'auto',
  fontSize: 12,
} as const
