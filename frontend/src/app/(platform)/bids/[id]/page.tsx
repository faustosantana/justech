'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

const API = process.env.NEXT_PUBLIC_API_BASE || '/api/v1';

export default function BidDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [bid, setBid] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [interest, setInterest] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const r = await fetch(`${API}/bids/${id}`, { credentials: 'include' });
        setBid(await r.json());
        const a = await fetch(`${API}/bids/${id}/analysis`, { credentials: 'include' });
        setAnalysis(await a.json());
      } catch (e: any) {
        setError(e?.message);
      }
    })();
  }, [id]);

  async function showInterest() {
    if (!id || busy) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/bids/${id}/interest`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': `ui-detail-${id}` },
        body: JSON.stringify({ origin: 'jaios', idempotency_key: `ui-detail-${id}` }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setInterest(data);
    } catch (e: any) {
      setError(e?.message);
    } finally {
      setBusy(false);
    }
  }

  if (!bid) return <main style={{ padding: '1.5rem' }}>Cargando…</main>;

  const inOdoo = !!(interest?.odoo_tender_id || bid.odoo_tender_id);

  return (
    <main style={{ padding: '1.5rem', maxWidth: 900, margin: '0 auto', fontFamily: 'Georgia, serif' }}>
      <a href="/bids">← Licitaciones</a>
      <h1>{bid.title}</h1>
      <p>
        {bid.institution_name} · {bid.process_number} · {bid.submission_deadline}
      </p>
      <p>{bid.summary}</p>
      <section>
        <h2>Requisitos / riesgos</h2>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(analysis, null, 2)}</pre>
      </section>
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
        {!inOdoo ? (
          <button type="button" disabled={busy} onClick={showInterest}>
            {busy ? '…' : 'Mostrar interés'}
          </button>
        ) : (
          interest?.odoo_url && (
            <a href={interest.odoo_url} target="_blank" rel="noreferrer">
              Continuar en Odoo
            </a>
          )
        )}
        {bid.source_url && (
          <a href={bid.source_url} target="_blank" rel="noreferrer">
            Abrir fuente
          </a>
        )}
      </div>
      {error && <p style={{ color: '#a33' }}>{error}</p>}
    </main>
  );
}
