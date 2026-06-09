import { useEffect, useState } from "react";

import { JaiosLogo } from "../components/JaiosLogo";
import { desktopApi, type SessionState } from "../lib/desktop-api";

type Props = {
  onChangeServer: () => void;
};

export function LoginView({ onChangeServer }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connStatus, setConnStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [session, setSession] = useState<SessionState | null>(null);

  useEffect(() => {
    desktopApi.getSessionState().then((s) => {
      setSession(s);
      setRemember(s.remember_session);
      if (s.authenticated) {
        desktopApi.enterApp().catch(() => undefined);
      }
    });
  }, []);

  async function testConnection() {
    setTesting(true);
    setError(null);
    setConnStatus(null);
    try {
      const test = await desktopApi.testServerConnection();
      setConnStatus(test.ok ? test.message : null);
      if (!test.ok) setError(test.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setTesting(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const cfg = await desktopApi.getAppConfig();
      await desktopApi.saveAppConfig({
        ...cfg,
        remember_session: remember,
        setup_completed: true,
      });
      await desktopApi.completeSetup().catch(() => undefined);
      await desktopApi.login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-bg" aria-hidden />
      <div className="login-shell">
        <header className="login-header">
          <JaiosLogo size={52} />
          <h1>Bienvenido a JAIOS</h1>
          <p>Conecta con el centro operativo de Justech</p>
        </header>

        <form className="login-card" onSubmit={submit}>
          <label htmlFor="email">Correo</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="nombre@justech.do"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <label htmlFor="tenant">Empresa</label>
          <input
            id="tenant"
            type="text"
            value={session?.tenant_slug ?? "justech"}
            readOnly
            className="input-muted"
          />

          <label className="checkbox-row login-checkbox">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            <span>Recordar sesión en esta computadora</span>
          </label>

          <button type="submit" className="btn-primary btn-full" disabled={loading}>
            {loading ? "Entrando…" : "Entrar a JAIOS"}
          </button>

          <div className="login-secondary">
            <button type="button" className="btn-link" onClick={onChangeServer}>
              Cambiar servidor
            </button>
            <button type="button" className="btn-link" disabled={testing} onClick={testConnection}>
              {testing ? "Probando…" : "Probar conexión"}
            </button>
          </div>

          {connStatus && <p className="status ok">{connStatus}</p>}
          {error && <p className="status error">{error}</p>}

          <p className="login-footnote">Tu contraseña no se guarda en esta computadora.</p>
        </form>

        {session?.web_url && (
          <p className="server-badge" title={session.web_url}>
            Servidor: {session.web_url.replace(/^https?:\/\//, "")}
          </p>
        )}
      </div>
    </div>
  );
}
