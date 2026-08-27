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


ACTION_LABELS = {"buy": "買い", "sell": "売り"}


def build_signal_email_html(signals: list) -> str:
    sections = []
    for signal in signals:
        action_label = ACTION_LABELS[signal["action"]]
        reasons_html = "".join(f"<li>{reason}</li>" for reason in signal["reasons"])
        stop_loss_html = (
            f"<p>損切りライン: {signal['stop_loss_label']}</p>" if signal.get("stop_loss_label") else ""
        )
        sections.append(
            f"<h3>{signal['target']}（{action_label}シグナル）</h3>"
            f"<p>URL: <a href=\"{signal['url']}\">{signal['url']}</a></p>"
            f"<p>価格: {signal['price_label']}</p>"
            f"<p>判断理由:</p><ul>{reasons_html}</ul>"
            f"{stop_loss_html}"
            "<p style=\"color:#64708a;font-size:0.85em;\">"
            "本シグナルはK線パターンに基づく機械的な判定であり、投資助言ではありません。"
            "最終的な売買判断はご自身の責任で行ってください。"
            "</p>"
        )
    return "<div>" + "".join(sections) + "</div>"


def send_signal_notification(signals: list, api_key: str, from_email: str, to_email: str) -> dict:
    if not signals:
        raise NotificationError("No signals to notify")

    targets = "、".join(signal["target"] for signal in signals)
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": f"[K線シグナル] 買い/売りシグナル発生: {targets}",
        "html": build_signal_email_html(signals),
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
