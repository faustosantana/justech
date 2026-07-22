'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

type Bid = {
  jaios_tender_id?: string;
  external_id: string;
  title: string;
  institution_name: string;
  process_number?: string;
  submission_deadline?: string;
  estimated_budget?: number;
  currency?: string;
  compatibility_score?: number;
  workflow_status?: string;
  interest_status?: string;
  summary?: string;
  odoo_tender_id?: number | null;
};

type InterestResult = {
  ok: boolean;
  odoo_tender_id?: number | null;
  odoo_url?: string | null;
  workflow_status?: string;
  detail?: string;
  idempotent?: boolean;
};

const API = process.env.NEXT_PUBLIC_API_BASE || '/api/v1';

export default function BidsPage() {
  const [items, setItems] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'recommended' | 'interest' | 'odoo'>('all');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [interestMap, setInterestMap] = useState<Record<string, InterestResult>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/bids?page_size=50`, { credentials: 'include' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error cargando licitaciones');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const visible = useMemo(() => {
    return items.filter((b) => {
      if (filter === 'recommended') return (b.compatibility_score || 0) >= 70;
      if (filter === 'interest') return b.interest_status === 'interested' || !!interestMap[b.external_id]?.odoo_tender_id;
      if (filter === 'odoo') return !!(b.odoo_tender_id || interestMap[b.external_id]?.odoo_tender_id);
      return true;
    });
  }, [items, filter, interestMap]);

  async function showInterest(bid: Bid) {
    const id = bid.jaios_tender_id || bid.external_id;
    if (busyId) return;
    setBusyId(id);
    try {
      const res = await fetch(`${API}/bids/${id}/interest`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `ui-${id}`,
        },
        body: JSON.stringify({ origin: 'jaios', idempotency_key: `ui-${id}` }),
      });
      const data = (await res.json()) as InterestResult;
      if (!res.ok) throw new Error((data as any).detail || `HTTP ${res.status}`);
      setInterestMap((m) => ({ ...m, [bid.external_id]: data }));
    } catch (e: any) {
      setError(e?.message || 'No se pudo registrar interés');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main style={{ padding: '1.5rem', maxWidth: 1100, margin: '0 auto', fontFamily: 'Georgia, serif' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.25rem' }}>Licitaciones</h1>
      <p style={{ opacity: 0.75, marginBottom: '1.25rem' }}>
        Descubrimiento en JAIOS · gestión completa en Odoo Bid Center
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {([
          ['all', 'Todas'],
          ['recommended', 'Recomendadas'],
          ['interest', 'Con interés'],
          ['odoo', 'En Odoo'],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setFilter(k)}
            style={{
              padding: '0.4rem 0.8rem',
              border: filter === k ? '2px solid #1a1a1a' : '1px solid #ccc',
              background: filter === k ? '#f3f0e8' : '#fff',
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
        <button type="button" onClick={load} style={{ marginLeft: 'auto', cursor: 'pointer' }}>
          Actualizar
        </button>
      </div>

      {loading && <p>Cargando…</p>}
      {error && <p style={{ color: '#a33' }}>{error}</p>}

      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {visible.map((b) => {
          const id = b.jaios_tender_id || b.external_id;
          const interest = interestMap[b.external_id];
          const inOdoo = !!(b.odoo_tender_id || interest?.odoo_tender_id);
          const odooUrl = interest?.odoo_url;
          return (
            <article
              key={id}
              style={{
                borderBottom: '1px solid #ddd',
                paddingBottom: '0.75rem',
                display: 'grid',
                gap: '0.35rem',
              }}
            >
              <strong>{b.title}</strong>
              <span>
                {b.institution_name} · {b.process_number || '—'} · cierre {b.submission_deadline || '—'}
              </span>
              <span>
                Presupuesto {b.estimated_budget ?? '—'} {b.currency || ''} · compat{' '}
                {b.compatibility_score ?? '—'} · {b.workflow_status || 'discovered'}
              </span>
              {b.summary && <p style={{ margin: 0, opacity: 0.85 }}>{b.summary.slice(0, 220)}</p>}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {!inOdoo ? (
                  <button
                    type="button"
                    disabled={busyId === id}
                    onClick={() => showInterest(b)}
                    style={{ padding: '0.45rem 0.9rem', cursor: 'pointer' }}
                  >
                    {busyId === id ? 'Registrando…' : 'Mostrar interés'}
                  </button>
                ) : (
                  <>
                    <span style={{ alignSelf: 'center' }}>En Odoo #{interest?.odoo_tender_id || b.odoo_tender_id}</span>
                    {odooUrl && (
                      <a href={odooUrl} target="_blank" rel="noreferrer" style={{ padding: '0.45rem 0.9rem' }}>
                        Continuar en Odoo
                      </a>
                    )}
                  </>
                )}
                <a href={`/bids/${id}`} style={{ padding: '0.45rem 0.9rem' }}>
                  Detalle
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}
