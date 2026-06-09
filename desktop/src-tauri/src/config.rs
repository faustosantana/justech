use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Servidor JAIOS Justech (Tailscale / LAN interna).
pub const DEFAULT_WEB_URL: &str = "http://100.81.128.32:3000";
/// Dominio producción futuro (HTTPS).
pub const PRODUCTION_WEB_URL: &str = "https://jaios.justech.do";
pub const DEFAULT_TENANT: &str = "justech";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub web_url: String,
    pub api_url: String,
    pub tenant_slug: String,
    pub remember_session: bool,
    pub clear_on_exit: bool,
    pub require_https: bool,
    /// Primera pantalla de bienvenida completada (conexión probada).
    #[serde(default)]
    pub setup_completed: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        let web_url = std::env::var("JAIOS_SERVER_URL").unwrap_or_else(|_| DEFAULT_WEB_URL.into());
        let api_url = derive_api_url(&web_url);
        Self {
            web_url,
            api_url,
            tenant_slug: DEFAULT_TENANT.into(),
            remember_session: true,
            clear_on_exit: false,
            require_https: false,
            setup_completed: true,
        }
    }
}

pub fn config_path() -> Result<PathBuf, String> {
    let dir = dirs::data_dir()
        .ok_or_else(|| "No se pudo resolver directorio de datos".to_string())?
        .join("com.justech.jaios");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join("config.json"))
}

pub fn cache_dir() -> Result<PathBuf, String> {
    let dir = dirs::cache_dir()
        .ok_or_else(|| "No se pudo resolver caché".to_string())?
        .join("com.justech.jaios");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

pub fn load_config() -> AppConfig {
    let path = match config_path() {
        Ok(p) => p,
        Err(_) => return AppConfig::default(),
    };
    if !path.exists() {
        return AppConfig::default();
    }
    let raw = fs::read_to_string(&path).unwrap_or_default();
    serde_json::from_str(&raw).unwrap_or_default()
}

pub fn save_config(config: &AppConfig) -> Result<(), String> {
    validate_server_url(&config.web_url, config.require_https)?;
    let path = config_path()?;
    let raw = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    fs::write(path, raw).map_err(|e| e.to_string())
}

pub fn derive_api_url(web_url: &str) -> String {
    let trimmed = web_url.trim().trim_end_matches('/');
    if trimmed.ends_with("/api/v1") {
        return trimmed.to_string();
    }
    if let Ok(mut parsed) = url::Url::parse(trimmed) {
        if parsed.port() == Some(3000) {
            let _ = parsed.set_port(Some(8000));
            let base = parsed.as_str().trim_end_matches('/');
            return format!("{base}/api/v1");
        }
        return format!("{trimmed}/api/v1");
    }
    format!("{trimmed}/api/v1")
}

pub fn validate_server_url(web_url: &str, require_https: bool) -> Result<(), String> {
    let trimmed = web_url.trim();
    if trimmed.is_empty() {
        return Err("Ingrese la URL del servidor JAIOS".into());
    }
    url::Url::parse(trimmed).map_err(|_| "URL inválida".to_string())?;
    if require_https
        && !trimmed.starts_with("https://")
        && !trimmed.contains("localhost")
        && !trimmed.contains("127.0.0.1")
    {
        return Err("En producción debe usar HTTPS".into());
    }
    Ok(())
}

pub fn is_configured(config: &AppConfig) -> bool {
    !config.web_url.trim().is_empty() && !config.api_url.trim().is_empty()
}

pub fn reset_to_defaults() -> AppConfig {
    AppConfig::default()
}
