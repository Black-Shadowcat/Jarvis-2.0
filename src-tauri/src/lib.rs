use std::time::Duration;

const BACKEND: &str = "http://localhost:8340";
const TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Debug, serde::Serialize)]
pub struct ApiError {
    pub message: String,
}

impl From<reqwest::Error> for ApiError {
    fn from(e: reqwest::Error) -> Self {
        ApiError { message: e.to_string() }
    }
}

fn http_client() -> Result<reqwest::Client, ApiError> {
    reqwest::Client::builder()
        .timeout(TIMEOUT)
        .build()
        .map_err(ApiError::from)
}

async fn get_json(path: &str) -> Result<serde_json::Value, ApiError> {
    let c = http_client()?;
    let url = format!("{BACKEND}{path}");
    let resp = c.get(&url).send().await.map_err(ApiError::from)?;
    resp.json::<serde_json::Value>().await.map_err(ApiError::from)
}

mod commands {
    use super::{get_json, http_client, ApiError, BACKEND};

    #[tauri::command]
    pub async fn get_status() -> Result<serde_json::Value, ApiError> {
        get_json("/api/supervisor/status").await
    }

    #[tauri::command]
    pub async fn get_version() -> Result<serde_json::Value, ApiError> {
        get_json("/api/version").await
    }

    #[tauri::command]
    pub async fn send_chat(message: String) -> Result<serde_json::Value, ApiError> {
        let c = http_client()?;
        let url = format!("{BACKEND}/api/chat");
        let body = serde_json::json!({ "message": message });
        let resp = c.post(&url).json(&body).send().await.map_err(ApiError::from)?;
        resp.json::<serde_json::Value>().await.map_err(ApiError::from)
    }
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::get_status,
            commands::get_version,
            commands::send_chat,
        ])
        .setup(|app| {
            tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::App("/".into()))
                .title("Jarvis")
                .inner_size(1920.0, 1200.0)
                .min_inner_size(600.0, 500.0)
                .resizable(true)
                .fullscreen(true)
                .center()
                .initialization_script(
                    "document.addEventListener('keydown',function(e){\
                        if((e.metaKey||e.ctrlKey)&&e.key==='r'){\
                            e.preventDefault();location.reload();\
                        }\
                    });",
                )
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Fehler beim Starten der Jarvis-App");
}
