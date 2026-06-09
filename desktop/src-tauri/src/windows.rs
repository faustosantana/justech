use std::fs;

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

use crate::auth::{auth_injection_script, StoredSession};
use crate::config::{cache_dir, load_config};

const LAUNCHER: &str = "launcher";
const MAIN: &str = "main";
const ASSISTANT: &str = "assistant";

pub fn open_launcher(app: &AppHandle) -> Result<(), String> {
    if let Some(win) = app.get_webview_window(LAUNCHER) {
        let _ = win.show();
        let _ = win.set_focus();
        return Ok(());
    }
    WebviewWindowBuilder::new(app, LAUNCHER, WebviewUrl::App("index.html".into()))
        .title("JAIOS Desktop")
        .inner_size(520.0, 680.0)
        .resizable(true)
        .center()
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub fn open_main(app: &AppHandle, session: &StoredSession) -> Result<(), String> {
    let config = load_config();
    let target = format!("{}/dashboard", config.web_url.trim_end_matches('/'));
    let script = auth_injection_script(session);
    if let Some(win) = app.get_webview_window(MAIN) {
        let _ = win.eval(&script);
        let _ = win.show();
        let _ = win.set_focus();
        return Ok(());
    }
    let parsed: url::Url = target.parse().map_err(|e: url::ParseError| e.to_string())?;
    WebviewWindowBuilder::new(app, MAIN, WebviewUrl::External(parsed))
        .title("JAIOS")
        .inner_size(1320.0, 860.0)
        .resizable(true)
        .center()
        .initialization_script(&script)
        .build()
        .map_err(|e| e.to_string())?;
    if let Some(launcher) = app.get_webview_window(LAUNCHER) {
        let _ = launcher.hide();
    }
    Ok(())
}

pub fn open_assistant(app: &AppHandle) -> Result<(), String> {
    if let Some(win) = app.get_webview_window(ASSISTANT) {
        let visible = win.is_visible().unwrap_or(false);
        if visible {
            let _ = win.hide();
        } else {
            let _ = win.show();
            let _ = win.set_focus();
        }
        return Ok(());
    }
    WebviewWindowBuilder::new(app, ASSISTANT, WebviewUrl::App("index.html#/assistant".into()))
        .title("JAIOS Assistant")
        .inner_size(420.0, 680.0)
        .always_on_top(true)
        .resizable(true)
        .center()
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub fn hide_assistant(app: &AppHandle) {
    if let Some(win) = app.get_webview_window(ASSISTANT) {
        let _ = win.hide();
    }
}

pub fn logout_close_main(app: &AppHandle) {
    if let Some(win) = app.get_webview_window(MAIN) {
        let _ = win.close();
    }
    if let Some(win) = app.get_webview_window(ASSISTANT) {
        let _ = win.close();
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct AssistantMessage {
    pub role: String,
    pub content: String,
    pub timestamp: String,
}

pub fn load_assistant_history() -> Vec<AssistantMessage> {
    let path = match cache_dir() {
        Ok(dir) => dir.join("assistant_history.json"),
        Err(_) => return vec![],
    };
    if !path.exists() {
        return vec![];
    }
    let raw = fs::read_to_string(path).unwrap_or_default();
    serde_json::from_str(&raw).unwrap_or_default()
}

pub fn save_assistant_history(items: &[AssistantMessage]) -> Result<(), String> {
    let path = cache_dir()?.join("assistant_history.json");
    let raw = serde_json::to_string_pretty(items).map_err(|e| e.to_string())?;
    fs::write(path, raw).map_err(|e| e.to_string())
}
