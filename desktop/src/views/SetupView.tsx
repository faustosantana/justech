import { useEffect, useState } from "react";

import { JaiosLogo } from "../components/JaiosLogo";
import { desktopApi, type AppConfig } from "../lib/desktop-api";

type Props = {
  onDone: () => void;
};

export function SetupView({ onDone }: Props) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [connectionOk, setConnectionOk] = useState(false);

  useEffect(() => {
    desktopApi.getAppConfig().then(setConfig);
  }, []);

  if (!config) return <div className="shell">Cargando…</div>;

  async function testConnection() {
    setLoading(true);
    setError(null);
    setStatus(null);
    setConnectionOk(false);
    try {
      await desktopApi.saveAppConfig(config);
      const test = await desktopApi.testServerConnection();
      if (!test.ok) {
        setError(test.message);
        return;
      }
      setStatus(test.message);
      setConnectionOk(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function continueToLogin() {
    if (!connectionOk) {
      await testConnection();
      return;
    }
    setLoading(true);
    try {
      await desktopApi.completeSetup();
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="shell">
      <div className="brand">
        <JaiosLogo size={44} showWordmark={false} />
        <div>
          <h1>Configuración del servidor</h1>
          <p>Cambia la conexión al centro JAIOS</p>
        </div>
      </div>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Servidor detectado</h2>
        <div className="server-detected">{config.web_url}</div>
        <p className="hint">
          Empresa: <strong>{config.tenant_slug}</strong> — no necesita Docker ni base de datos local.
        </p>

        <div className="actions">
          <button className="secondary" disabled={loading} onClick={testConnection}>
            Probar conexión
          </button>
          <button className="primary" disabled={loading || !connectionOk} onClick={continueToLogin}>
            Guardar y volver al login
          </button>
        </div>

        {status && <p className="status ok">{status}</p>}
        {error && <p className="status error">{error}</p>}

        <button type="button" className="link-btn" onClick={() => setAdvanced((v) => !v)}>
          {advanced ? "Ocultar configuración avanzada" : "Configuración avanzada"}
        </button>

        {advanced && (
          <div className="advanced-panel">
            <label htmlFor="web_url">URL del servidor JAIOS</label>
            <input
              id="web_url"
              type="url"
              value={config.web_url}
              onChange={(e) => {
                setConnectionOk(false);
                setConfig({ ...config, web_url: e.target.value });
              }}
            />
            <label htmlFor="tenant">Empresa (tenant)</label>
            <input
              id="tenant"
              type="text"
              value={config.tenant_slug}
              onChange={(e) => setConfig({ ...config, tenant_slug: e.target.value })}
            />
            <div className="checkbox-row">
              <input
                id="https"
                type="checkbox"
                checked={config.require_https}
                onChange={(e) => setConfig({ ...config, require_https: e.target.checked })}
              />
              <label htmlFor="https">Exigir HTTPS (producción)</label>
            </div>
            <p className="version">Producción futura: https://jaios.justech.do</p>
            <p className="version">API: {config.api_url}</p>
            <button
              type="button"
              className="ghost danger"
              disabled={loading}
              onClick={async () => {
                if (!confirm("¿Restablecer configuración y cerrar sesión?")) return;
                await desktopApi.resetAppConfig();
                const cfg = await desktopApi.getAppConfig();
                setConfig(cfg);
                setConnectionOk(false);
                setStatus(null);
                setError(null);
              }}
            >
              Restablecer configuración
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
