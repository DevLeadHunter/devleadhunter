// Prod → local DB sync is a local dev tool only: the module is compiled out of release
// builds (debug_assertions is false in `tauri build --release`).
#[cfg(debug_assertions)]
mod db_sync;

// The WebView2 permission plumbing only exists on Windows.
#[cfg(windows)]
mod media_permissions;

/// Sync the local dev database from prod (mysqldump → import). The command always exists
/// (so the frontend can `invoke` it), but only runs in debug builds; in a release build it
/// returns an error instead — the desktop app never syncs against a user's machine in prod.
#[tauri::command]
fn sync_dev_database_from_prod() -> Result<String, String> {
    #[cfg(debug_assertions)]
    {
        db_sync::sync_dev_database_from_prod_impl()
    }
    #[cfg(not(debug_assertions))]
    {
        Err("Prod → local DB sync is only available in debug builds (`tauri:dev`).".into())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![sync_dev_database_from_prod])
        .setup(|_app| {
            // Sans ça, `getUserMedia` (enregistrement du clip de prospection)
            // ne peut pas ouvrir la caméra dans l'app desktop.
            #[cfg(windows)]
            {
                use tauri::Manager;
                if let Some(window) = _app.get_webview_window("main") {
                    media_permissions::grant_camera_and_microphone(&window);
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
