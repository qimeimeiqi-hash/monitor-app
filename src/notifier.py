import requests

RESEND_API_URL = "https://api.resend.com/emails"


class NotificationError(Exception):
    pass


def build_email_html(changes: list) -> str:
    sections = []
    for change in changes:
        sections.append(
            f"<h3>{change['target']}</h3>"
            f"<p>URL: <a href=\"{change['url']}\">{change['url']}</a></p>"
            f"<p>旧内容: {change['old_value']}</p>"
            f"<p>新内容: {change['new_value']}</p>"
        )
    return "<div>" + "".join(sections) + "</div>"


def send_change_notification(changes: list, api_key: str, from_email: str, to_email: str) -> dict:
    if not changes:
        raise NotificationError("No changes to notify")

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": f"[监测提醒] {len(changes)} 个目标发生变动",
        "html": build_email_html(changes),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException as request_error:
        raise NotificationError(f"Failed to call Resend API: {request_error}") from request_error

    if response.status_code >= 400:
        raise NotificationError(f"Resend API returned {response.status_code}: {response.text}")

    return response.json()
