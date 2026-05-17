pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("Fehler beim Starten der Jarvis-App");
}
