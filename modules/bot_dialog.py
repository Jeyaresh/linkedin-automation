'''
Bot dialog helper - shows dialogs via web UI when Flask is running, falls back to pyautogui otherwise.
'''
import time
import urllib.request
import urllib.error
import json

WEB_UI_URL = "http://127.0.0.1:5000"


def _try_web_dialog(dialog_type: str, title: str, message: str, buttons: list) -> str | None:
    """Try to show dialog via web UI. Returns response or None if web UI unavailable."""
    try:
        data = json.dumps({
            "type": dialog_type,
            "title": title,
            "message": message,
            "buttons": buttons
        }).encode()
        req = urllib.request.Request(
            f"{WEB_UI_URL}/bot/request-dialog",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            resp = json.loads(r.read().decode())
            dialog_id = resp.get("dialog_id")
            if not dialog_id:
                return None
        # Poll for response
        while True:
            time.sleep(0.5)
            req = urllib.request.Request(f"{WEB_UI_URL}/bot/check-response?id={dialog_id}")
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
                if resp.get("ready"):
                    return resp.get("response", buttons[0] if buttons else "OK")
    except Exception:
        return None


def web_alert(title: str, message: str, button: str = "OK") -> None:
    """Show alert - uses web UI if available, else pyautogui."""
    from pyautogui import alert
    response = _try_web_dialog("alert", title, message, [button])
    if response is None:
        alert(text=message, title=title, button=button)


def web_confirm(title: str, message: str, buttons: list) -> str:
    """Show confirm - uses web UI if available, else pyautogui. Returns chosen button text."""
    from pyautogui import confirm
    response = _try_web_dialog("confirm", title, message, buttons)
    if response is not None:
        return response
    return confirm(message, title, buttons)
