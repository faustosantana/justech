use serde::{Deserialize, Serialize};

const SERVICE: &str = "jaios-desktop";

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StoredSession {
    pub access_token: Option<String>,
    pub refresh_token: Option<String>,
    pub tenant_id: Option<String>,
    pub role: Option<String>,
}

fn entry(account: &str) -> Result<keyring::Entry, String> {
    keyring::Entry::new(SERVICE, account).map_err(|e| e.to_string())
}

pub fn store_session(session: &StoredSession) -> Result<(), String> {
    if let Some(token) = &session.access_token {
        entry("access_token")?.set_password(token).map_err(|e| e.to_string())?;
    }
    if let Some(token) = &session.refresh_token {
        entry("refresh_token")?.set_password(token).map_err(|e| e.to_string())?;
    }
    if let Some(tid) = &session.tenant_id {
        entry("tenant_id")?.set_password(tid).map_err(|e| e.to_string())?;
    }
    if let Some(role) = &session.role {
        entry("role")?.set_password(role).map_err(|e| e.to_string())?;
    }
    Ok(())
}

pub fn load_session() -> StoredSession {
    let access_token = entry("access_token").ok().and_then(|e| e.get_password().ok());
    let refresh_token = entry("refresh_token").ok().and_then(|e| e.get_password().ok());
    let tenant_id = entry("tenant_id").ok().and_then(|e| e.get_password().ok());
    let role = entry("role").ok().and_then(|e| e.get_password().ok());
    StoredSession {
        access_token,
        refresh_token,
        tenant_id,
        role,
    }
}

pub fn clear_session() -> Result<(), String> {
    for account in ["access_token", "refresh_token", "tenant_id", "role"] {
        if let Ok(e) = entry(account) {
            let _ = e.delete_credential();
        }
    }
    Ok(())
}

pub fn has_session() -> bool {
    load_session().access_token.is_some()
}

pub fn auth_injection_script(session: &StoredSession) -> String {
    let access = session.access_token.as_deref().unwrap_or("");
    let refresh = session.refresh_token.as_deref().unwrap_or("");
    let tenant = session.tenant_id.as_deref().unwrap_or("");
    let role = session.role.as_deref().unwrap_or("");
    format!(
        r#"(function() {{
  try {{
    localStorage.setItem('jaios_access_token', {access});
    localStorage.setItem('jaios_refresh_token', {refresh});
    localStorage.setItem('jaios_tenant_id', {tenant});
    localStorage.setItem('jaios_role', {role});
  }} catch (e) {{}}
}})();"#,
        access = serde_json::to_string(access).unwrap_or_default(),
        refresh = serde_json::to_string(refresh).unwrap_or_default(),
        tenant = serde_json::to_string(tenant).unwrap_or_default(),
        role = serde_json::to_string(role).unwrap_or_default(),
    )
}
