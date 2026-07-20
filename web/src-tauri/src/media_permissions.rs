//! Grants the WebView2 camera/microphone permission in the desktop build.
//!
//! The presenter-clip recorder calls `getUserMedia`, and WebView2 raises
//! `PermissionRequested` for it. wry (0.55) only handles that event to allow
//! clipboard reads, so without this the request falls back to WebView2's
//! default handling and the camera may never open in the packaged app.
//!
//! Granting it here is not a silent decision: the app asks in its own UI
//! ("Activer ma caméra") before any capture starts, and nothing is recorded
//! until the user starts a take.

use tauri::WebviewWindow;
use webview2_com::Microsoft::Web::WebView2::Win32::{
    COREWEBVIEW2_PERMISSION_KIND, COREWEBVIEW2_PERMISSION_KIND_CAMERA,
    COREWEBVIEW2_PERMISSION_KIND_MICROPHONE, COREWEBVIEW2_PERMISSION_STATE_ALLOW,
};
use webview2_com::PermissionRequestedEventHandler;

/// Allow camera and microphone requests coming from the app's own pages.
///
/// Failures are logged and swallowed: a desktop window that cannot register
/// the handler must still open — the user can always fall back to importing a
/// video file instead of recording one.
pub fn grant_camera_and_microphone(window: &WebviewWindow) {
    let result = window.with_webview(|webview| unsafe {
        let controller = webview.controller();
        let core = match controller.CoreWebView2() {
            Ok(core) => core,
            Err(error) => {
                eprintln!("[media] cannot reach CoreWebView2: {error}");
                return;
            }
        };

        let mut token: i64 = 0;
        let registration = core.add_PermissionRequested(
            &PermissionRequestedEventHandler::create(Box::new(|_, args| {
                let Some(args) = args else { return Ok(()) };

                let mut kind = COREWEBVIEW2_PERMISSION_KIND::default();
                args.PermissionKind(&mut kind)?;
                if kind == COREWEBVIEW2_PERMISSION_KIND_CAMERA
                    || kind == COREWEBVIEW2_PERMISSION_KIND_MICROPHONE
                {
                    args.SetState(COREWEBVIEW2_PERMISSION_STATE_ALLOW)?;
                }

                Ok(())
            })),
            &mut token,
        );

        if let Err(error) = registration {
            eprintln!("[media] cannot register PermissionRequested: {error}");
        }
    });

    if let Err(error) = result {
        eprintln!("[media] cannot access the webview: {error}");
    }
}
