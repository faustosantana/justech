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

  if (!config) {
    return (
      <div className="login-page">
        <div className="login-bg" aria-hidden />
        <p className="login-loading">Cargando…</p>
      </div>
    );
  }

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

  async function saveAndReturn() {
    if (!connectionOk) {
      await testConnection();
      if (!connectionOk) return;
    }
    setLoading(true);
    try {
      await desktopApi.saveAppConfig({ ...config, setup_completed: true });
      await desktopApi.completeSetup();
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-bg" aria-hidden />
      <div className="login-shell">
        <header className="login-header">
          <JaiosLogo size={48} />
          <h1>Cambiar servidor</h1>
          <p>Conecta JAIOS al centro operativo de tu empresa</p>
        </header>

        <div className="login-card">
          <p className="setup-server-label">Servidor actual</p>
          <div className="server-detected">{config.web_url}</div>
          <p className="setup-hint">
            Empresa: <strong>{config.tenant_slug}</strong>
          </p>

          <div className="login-secondary setup-actions">
            <button type="button" className="btn-link" disabled={loading} onClick={testConnection}>
              {loading ? "Probando…" : "Probar conexión"}
            </button>
            <button type="button" className="btn-link" onClick={() => setAdvanced((v) => !v)}>
              {advanced ? "Ocultar avanzado" : "Configuración avanzada"}
            </button>
          </div>

          {advanced && (
            <div className="advanced-panel">
              <label htmlFor="web_url">URL del servidor</label>
              <input
                id="web_url"
                type="url"
                value={config.web_url}
                onChange={(e) => {
                  setConnectionOk(false);
                  setConfig({ ...config, web_url: e.target.value });
                }}
              />
              <label htmlFor="tenant">Empresa / Tenant</label>
              <input
                id="tenant"
                type="text"
                value={config.tenant_slug}
                onChange={(e) => setConfig({ ...config, tenant_slug: e.target.value })}
              />
              <label className="checkbox-row login-checkbox">
                <input
                  type="checkbox"
                  checked={config.require_https}
                  onChange={(e) => setConfig({ ...config, require_https: e.target.checked })}
                />
                <span>Exigir HTTPS (solo producción)</span>
              </label>
              <button
                type="button"
                className="btn-link danger-link"
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

          {status && <p className="status ok">{status}</p>}
          {error && <p className="status error">{error}</p>}

          <button type="button" className="btn-primary btn-full setup-save" disabled={loading} onClick={saveAndReturn}>
            {loading ? "Guardando…" : "Guardar y volver al login"}
          </button>

          <button type="button" className="btn-link setup-back" onClick={onDone}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
