# Rollback Workspace 1.0 (DEV)

1. Revertir tag/imagen DEV al commit/tag previo a Workspace 1.0 (Analyst 2.1 beta).
2. Quitar overlays `investigation_workspace/` y restaurar `hermes_decision_engine.py` / `lottery_chat_service.py` / `conversation_state.py` / `lottery.py` al tip Analyst 2.1.
3. Reiniciar API DEV; no tocar PROD.
4. Validar Cert200 residual smoke (LONG_30.T07–T10) sigue 4/4 sin workspace.
5. Si solo el fix de routing es el problema: revertir únicamente `speech_acts.py` + gate Hermes al commit anterior al fix.
