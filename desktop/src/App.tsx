import { useEffect, useState } from "react";

import { desktopApi, type SessionState } from "./lib/desktop-api";
import { AssistantView } from "./views/AssistantView";
import { LoginView } from "./views/LoginView";
import { SetupView } from "./views/SetupView";

type Route = "login" | "setup" | "assistant";

function resolveRoute(session: SessionState | null, manualSetup: boolean): Route {
  if (window.location.hash === "#/assistant") return "assistant";
  if (manualSetup) return "setup";
  return "login";
}

export default function App() {
  const [route, setRoute] = useState<Route>("login");
  const [session, setSession] = useState<SessionState | null>(null);
  const [manualSetup, setManualSetup] = useState(false);

  useEffect(() => {
    desktopApi
      .getSessionState()
      .then((s) => {
        setSession(s);
        setRoute(resolveRoute(s, false));
      })
      .catch(() => setRoute("login"));
  }, []);

  if (route === "assistant") return <AssistantView />;
  if (route === "setup") {
    return (
      <SetupView
        onDone={() => {
          setManualSetup(false);
          desktopApi.getSessionState().then((s) => {
            setSession(s);
            setRoute("login");
          });
        }}
      />
    );
  }
  return (
    <LoginView
      onChangeServer={() => {
        setManualSetup(true);
        setRoute("setup");
      }}
    />
  );
}
