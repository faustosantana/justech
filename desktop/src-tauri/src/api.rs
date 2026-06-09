use reqwest::multipart::{Form, Part};
use serde::{Deserialize, Serialize};

use crate::auth::StoredSession;
use crate::config::AppConfig;

#[derive(Debug, Serialize, Deserialize)]
pub struct ConnectionTestResult {
    pub ok: bool,
    pub message: String,
    pub api_url: String,
    pub web_url: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
    pub tenant_slug: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub tenant_id: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct NotificationItem {
    pub id: String,
    pub title: String,
    pub message: String,
    pub severity: Option<String>,
    pub created_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct NotificationList {
    pub items: Vec<NotificationItem>,
    pub total: i64,
    pub unread_count: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AssistantQueryRequest {
    pub question: String,
    pub current_module: Option<String>,
    pub conversation_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AssistantQueryResponse {
    pub answer: String,
    pub query_type: Option<String>,
    pub sources: Option<Vec<String>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UploadResult {
    pub document_id: String,
    pub title: String,
}

fn client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())
}

pub async fn test_connection(config: &AppConfig) -> ConnectionTestResult {
    let api = config.api_url.trim_end_matches('/');
    let health_url = format!("{api}/health");
    let client = match client() {
        Ok(c) => c,
        Err(e) => {
            return ConnectionTestResult {
                ok: false,
                message: e,
                api_url: config.api_url.clone(),
                web_url: config.web_url.clone(),
            };
        }
    };
    match client.get(&health_url).send().await {
        Ok(resp) if resp.status().is_success() => ConnectionTestResult {
            ok: true,
            message: "Conexión exitosa con el servidor JAIOS".into(),
            api_url: config.api_url.clone(),
            web_url: config.web_url.clone(),
        },
        Ok(resp) => ConnectionTestResult {
            ok: false,
            message: format!("Servidor respondió HTTP {}", resp.status()),
            api_url: config.api_url.clone(),
            web_url: config.web_url.clone(),
        },
        Err(_) => ConnectionTestResult {
            ok: false,
            message: "No se pudo conectar al servidor JAIOS.".into(),
            api_url: config.api_url.clone(),
            web_url: config.web_url.clone(),
        },
    }
}

pub async fn login(config: &AppConfig, req: LoginRequest) -> Result<TokenResponse, String> {
    let url = format!("{}/auth/login", config.api_url.trim_end_matches('/'));
    let client = client()?;
    let resp = client
        .post(&url)
        .json(&req)
        .send()
        .await
        .map_err(|e| format!("Error de red: {e}"))?;
    if !resp.status().is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(if body.is_empty() {
            "Credenciales inválidas".into()
        } else {
            body
        });
    }
    resp.json::<TokenResponse>()
        .await
        .map_err(|e| format!("Respuesta inválida: {e}"))
}

pub async fn fetch_notifications(
    config: &AppConfig,
    session: &StoredSession,
) -> Result<NotificationList, String> {
    let url = format!("{}/notifications?limit=20", config.api_url.trim_end_matches('/'));
    let client = client()?;
    let token = session
        .access_token
        .as_ref()
        .ok_or_else(|| "Sin sesión activa".to_string())?;
    let mut req = client.get(&url).header("Authorization", format!("Bearer {token}"));
    if let Some(tid) = &session.tenant_id {
        req = req.header("X-Tenant-Id", tid);
    }
    let resp = req.send().await.map_err(|e| e.to_string())?;
    if !resp.status().is_success() {
        return Err(format!("HTTP {}", resp.status()));
    }
    #[derive(Deserialize)]
    struct NotificationListRaw {
        items: Vec<NotificationItem>,
        total: i64,
        unread_count: i64,
    }
    let raw = resp.json::<NotificationListRaw>().await.map_err(|e| e.to_string())?;
    Ok(NotificationList {
        items: raw.items,
        total: raw.total,
        unread_count: raw.unread_count,
    })
}

pub async fn assistant_query(
    config: &AppConfig,
    session: &StoredSession,
    question: String,
) -> Result<AssistantQueryResponse, String> {
    let url = format!("{}/assistant/query", config.api_url.trim_end_matches('/'));
    let client = client()?;
    let token = session
        .access_token
        .as_ref()
        .ok_or_else(|| "Sin sesión activa".to_string())?;
    let body = AssistantQueryRequest {
        question,
        current_module: Some("/dashboard".into()),
        conversation_id: None,
    };
    let mut req = client
        .post(&url)
        .header("Authorization", format!("Bearer {token}"))
        .json(&body);
    if let Some(tid) = &session.tenant_id {
        req = req.header("X-Tenant-Id", tid);
    }
    let resp = req
        .send()
        .await
        .map_err(|_| "No se pudo conectar al servidor JAIOS.".to_string())?;
    if !resp.status().is_success() {
        return Err(format!("HTTP {}", resp.status()));
    }
    resp.json::<AssistantQueryResponse>()
        .await
        .map_err(|e| e.to_string())
}

pub async fn upload_bytes(
    config: &AppConfig,
    session: &StoredSession,
    filename: &str,
    bytes: Vec<u8>,
    title: &str,
) -> Result<UploadResult, String> {
    let url = format!("{}/documents", config.api_url.trim_end_matches('/'));
    let client = client()?;
    let token = session
        .access_token
        .as_ref()
        .ok_or_else(|| "Sin sesión activa".to_string())?;
    let part = Part::bytes(bytes)
        .file_name(filename.to_string())
        .mime_str("image/png")
        .map_err(|e| e.to_string())?;
    let form = Form::new()
        .part("file", part)
        .text("title", title.to_string())
        .text("category", "captura".to_string());
    let mut req = client
        .post(&url)
        .header("Authorization", format!("Bearer {token}"))
        .multipart(form);
    if let Some(tid) = &session.tenant_id {
        req = req.header("X-Tenant-Id", tid);
    }
    let resp = req.send().await.map_err(|e| e.to_string())?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(if body.is_empty() {
            format!("HTTP {}", status)
        } else {
            body
        });
    }
    #[derive(Deserialize)]
    struct DocResp {
        id: String,
        title: String,
    }
    let doc = resp.json::<DocResp>().await.map_err(|e| e.to_string())?;
    Ok(UploadResult {
        document_id: doc.id,
        title: doc.title,
    })
}
