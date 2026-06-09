mod api;
mod auth;
mod config;
mod windows;

use std::sync::Mutex;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, RunEvent, State,
};
use tauri_plugin_notification::NotificationExt;
use tauri_plugin_shell::ShellExt;

use api::{assistant_query, fetch_notifications, login, test_connection, LoginRequest, UploadResult};
use auth::{clear_session, has_session, load_session, store_session, StoredSession};
use config::{
    derive_api_url, is_configured, load_config, reset_to_defaults, save_config, validate_server_url,
    AppConfig, APP_VERSION,
};
use windows::{
    load_assistant_history, logout_close_main, open_assistant, open_launcher, open_main,
    save_assistant_history, AssistantMessage,
};

struct AppState {
    config: Mutex<AppConfig>,
    last_unread: Mutex<i64>,
}

#[derive(serde::Serialize)]
struct SessionState {
    configured: bool,
    authenticated: bool,
    web_url: String,
    api_url: String,
    tenant_slug: String,
    remember_session: bool,
    clear_on_exit: bool,
    require_https: bool,
    setup_completed: bool,
    version: String,
}

#[tauri::command]
fn get_session_state(state: State<AppState>) -> SessionState {
    let config = state.config.lock().unwrap().clone();
    SessionState {
        configured: is_configured(&config),
        authenticated: has_session(),
        web_url: config.web_url,
        api_url: config.api_url,
        tenant_slug: config.tenant_slug,
        remember_session: config.remember_session,
        clear_on_exit: config.clear_on_exit,
        require_https: config.require_https,
        setup_completed: config.setup_completed,
        version: APP_VERSION.into(),
    }
}

#[tauri::command]
fn get_app_config(state: State<AppState>) -> AppConfig {
    state.config.lock().unwrap().clone()
}

#[tauri::command]
fn save_app_config(state: State<AppState>, mut config: AppConfig) -> Result<ConnectionOk, String> {
    validate_server_url(&config.web_url, config.require_https)?;
    config.api_url = derive_api_url(&config.web_url);
    save_config(&config)?;
    *state.config.lock().unwrap() = config;
    Ok(ConnectionOk {
        ok: true,
        message: "Configuración guardada".into(),
    })
}

#[derive(serde::Serialize)]
struct ConnectionOk {
    ok: bool,
    message: String,
}

#[tauri::command]
async fn test_server_connection(state: State<'_, AppState>) -> Result<api::ConnectionTestResult, String> {
    let config = state.config.lock().unwrap().clone();
    Ok(test_connection(&config).await)
}

#[tauri::command]
fn reset_app_config(app: AppHandle, state: State<AppState>) -> Result<SessionState, String> {
    clear_session()?;
    logout_close_main(&app);
    let config = reset_to_defaults();
    save_config(&config)?;
    *state.config.lock().unwrap() = config;
    open_launcher(&app)?;
    Ok(get_session_state(state))
}

#[tauri::command]
async fn complete_setup(state: State<'_, AppState>) -> Result<SessionState, String> {
    let mut config = state.config.lock().unwrap().clone();
    config.setup_completed = true;
    save_config(&config)?;
    *state.config.lock().unwrap() = config.clone();
    Ok(get_session_state(state))
}

#[tauri::command]
async fn desktop_login(
    app: AppHandle,
    state: State<'_, AppState>,
    email: String,
    password: String,
) -> Result<SessionState, String> {
    let config = state.config.lock().unwrap().clone();
    if !is_configured(&config) {
        return Err("Configure el servidor JAIOS primero".into());
    }
    let resp = login(
        &config,
        LoginRequest {
            email,
            password,
            tenant_slug: Some(config.tenant_slug.clone()),
        },
    )
    .await?;
    let session = StoredSession {
        access_token: Some(resp.access_token),
        refresh_token: Some(resp.refresh_token),
        tenant_id: resp.tenant_id,
        role: resp.role,
    };
    store_session(&session)?;
    open_main(&app, &session)?;
    Ok(get_session_state(state))
}

#[tauri::command]
fn desktop_logout(app: AppHandle, state: State<AppState>) -> Result<SessionState, String> {
    clear_session()?;
    logout_close_main(&app);
    open_launcher(&app)?;
    Ok(get_session_state(state))
}

#[tauri::command]
async fn enter_app(app: AppHandle, state: State<'_, AppState>) -> Result<SessionState, String> {
    let session = load_session();
    if session.access_token.is_none() {
        return Err("Inicie sesión primero".into());
    }
    open_main(&app, &session)?;
    Ok(get_session_state(state))
}

#[tauri::command]
fn toggle_assistant(app: AppHandle) -> Result<(), String> {
    open_assistant(&app)
}

#[tauri::command]
async fn ask_assistant(state: State<'_, AppState>, question: String) -> Result<AssistantMessage, String> {
    let config = state.config.lock().unwrap().clone();
    let session = load_session();
    let resp = assistant_query(&config, &session, question).await?;
    let msg = AssistantMessage {
        role: "assistant".into(),
        content: resp.answer,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };
    Ok(msg)
}

#[tauri::command]
fn get_assistant_history() -> Vec<AssistantMessage> {
    load_assistant_history()
}

#[tauri::command]
fn append_assistant_history(user: AssistantMessage, assistant: AssistantMessage) -> Result<(), String> {
    let mut items = load_assistant_history();
    items.push(user);
    items.push(assistant);
    if items.len() > 80 {
        let drain = items.len() - 80;
        items.drain(0..drain);
    }
    save_assistant_history(&items)
}

#[tauri::command]
async fn get_notifications(state: State<'_, AppState>) -> Result<api::NotificationList, String> {
    let config = state.config.lock().unwrap().clone();
    let session = load_session();
    fetch_notifications(&config, &session).await
}

async fn perform_capture(app: AppHandle) {
    let png = capture_png_bytes();
    if png.is_empty() {
        let _ = app
            .notification()
            .builder()
            .title("JAIOS")
            .body("No se pudo capturar la pantalla")
            .show();
        return;
    }
    let state = app.state::<AppState>();
    let config = state.config.lock().unwrap().clone();
    let session = load_session();
    match api::upload_bytes(
        &config,
        &session,
        "jaios-desktop-capture.png",
        png,
        &format!("Captura desktop {}", chrono::Utc::now().format("%Y-%m-%d %H:%M")),
    )
    .await
    {
        Ok(doc) => {
            let _ = app
                .notification()
                .builder()
                .title("JAIOS")
                .body(format!("Documento subido: {}", doc.title))
                .show();
        }
        Err(e) => {
            let _ = app.notification().builder().title("JAIOS").body(&e).show();
        }
    }
}

fn capture_png_bytes() -> Vec<u8> {
    use screenshots::image::codecs::png::PngEncoder;
    use screenshots::image::ColorType;
    use screenshots::image::ImageEncoder;

    if let Ok(screens) = screenshots::Screen::all() {
        if let Some(screen) = screens.first() {
            if let Ok(image) = screen.capture() {
                let width = image.width();
                let height = image.height();
                let rgba = image.into_raw();
                let mut buf = Vec::new();
                let encoder = PngEncoder::new(&mut buf);
                if encoder
                    .write_image(&rgba, width, height, ColorType::Rgba8)
                    .is_ok()
                {
                    return buf;
                }
            }
        }
    }
    vec![]
}

#[tauri::command]
async fn capture_and_upload(app: AppHandle, state: State<'_, AppState>) -> Result<UploadResult, String> {
    let config = state.config.lock().unwrap().clone();
    let session = load_session();
    let png = capture_png_bytes();
    if png.is_empty() {
        return Err("No se pudo capturar la pantalla".into());
    }
    let title = format!("Captura desktop {}", chrono::Utc::now().format("%Y-%m-%d %H:%M"));
    api::upload_bytes(&config, &session, "jaios-desktop-capture.png", png, &title).await
}

#[tauri::command]
fn open_server_path(app: AppHandle, path: String) -> Result<(), String> {
    let config = load_config();
    let url = format!("{}{}", config.web_url.trim_end_matches('/'), path);
    app.shell().open(url, None).map_err(|e| e.to_string())
}

fn register_tray(app: &AppHandle) -> tauri::Result<()> {
    let open_i = MenuItem::with_id(app, "open", "Abrir JAIOS", true, None::<&str>)?;
    let ask_i = MenuItem::with_id(app, "ask", "Assistant", true, None::<&str>)?;
    let capture_i = MenuItem::with_id(app, "capture", "Capturar pantalla", true, None::<&str>)?;
    let logout_i = MenuItem::with_id(app, "logout", "Cerrar sesión", true, None::<&str>)?;
    let quit_i = MenuItem::with_id(app, "quit", "Salir", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open_i, &ask_i, &capture_i, &logout_i, &quit_i])?;

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("JAIOS Desktop")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => {
                let session = load_session();
                if session.access_token.is_some() {
                    let _ = open_main(app, &session);
                } else {
                    let _ = open_launcher(app);
                }
            }
            "ask" => {
                let _ = open_assistant(app);
            }
            "capture" => {
                let app = app.clone();
                tauri::async_runtime::spawn(async move {
                    perform_capture(app).await;
                });
            }
            "logout" => {
                let _ = clear_session();
                logout_close_main(app);
                let _ = open_launcher(app);
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                let session = load_session();
                if session.access_token.is_some() {
                    let _ = open_main(&app, &session);
                } else {
                    let _ = open_launcher(&app);
                }
            }
        })
        .build(app)?;
    Ok(())
}

fn register_shortcut(app: &AppHandle) -> Result<(), String> {
    #[cfg(desktop)]
    {
        use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};
        #[cfg(target_os = "macos")]
        let mods = Modifiers::SUPER | Modifiers::SHIFT;
        #[cfg(not(target_os = "macos"))]
        let mods = Modifiers::CONTROL | Modifiers::SHIFT;
        let shortcut = Shortcut::new(Some(mods), Code::KeyJ);
        app.global_shortcut()
            .register(shortcut)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn start_notification_poll(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        loop {
            tokio::time::sleep(std::time::Duration::from_secs(120)).await;
            if !has_session() {
                continue;
            }
            let state = app.state::<AppState>();
            let config = state.config.lock().unwrap().clone();
            let session = load_session();
            if let Ok(list) = fetch_notifications(&config, &session).await {
                let unread = list.items.len() as i64;
                let mut last = state.last_unread.lock().unwrap();
                if unread > *last {
                    let preview = list
                        .items
                        .first()
                        .map(|n| n.title.as_str())
                        .unwrap_or("Nuevas notificaciones JAIOS");
                    let _ = app
                        .notification()
                        .builder()
                        .title("JAIOS")
                        .body(preview)
                        .show();
                }
                *last = unread;
            }
        }
    });
}

fn bootstrap(app: &AppHandle) -> Result<(), String> {
    register_tray(app).map_err(|e| e.to_string())?;
    register_shortcut(app).map_err(|e| e.to_string())?;
    start_notification_poll(app.clone());
    let session = load_session();
    if has_session() && is_configured(&load_config()) {
        open_main(app, &session)?;
    } else {
        open_launcher(app)?;
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let initial = load_config();
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init());
    #[cfg(desktop)]
    let builder = builder.plugin(
        tauri_plugin_global_shortcut::Builder::new()
            .with_handler(|app, _shortcut, event| {
                use tauri_plugin_global_shortcut::ShortcutState;
                if event.state == ShortcutState::Pressed {
                    let _ = open_assistant(app);
                }
            })
            .build(),
    );
    builder
        .manage(AppState {
            config: Mutex::new(initial),
            last_unread: Mutex::new(0),
        })
        .invoke_handler(tauri::generate_handler![
            get_session_state,
            get_app_config,
            save_app_config,
            test_server_connection,
            complete_setup,
            reset_app_config,
            desktop_login,
            desktop_logout,
            enter_app,
            toggle_assistant,
            ask_assistant,
            get_assistant_history,
            append_assistant_history,
            get_notifications,
            capture_and_upload,
            open_server_path,
        ])
        .setup(|app| {
            bootstrap(app.handle())?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building JAIOS desktop")
        .run(|app, event| {
            match event {
                RunEvent::ExitRequested { api, .. } => {
                    api.prevent_exit();
                }
                RunEvent::Exit => {
                    let config = load_config();
                    if config.clear_on_exit || !config.remember_session {
                        let _ = clear_session();
                    }
                }
                _ => {}
            }
            let _ = app;
        });
}
