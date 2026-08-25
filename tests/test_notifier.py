from unittest.mock import Mock, patch

import pytest

from src.notifier import NotificationError, send_change_notification

SAMPLE_CHANGES = [
    {"target": "示例目标", "url": "https://example.com", "old_value": "旧", "new_value": "新"},
]


def test_send_change_notification_posts_expected_payload_and_auth_header():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"id": "email-123"}

    with patch("src.notifier.requests.post", return_value=mock_response) as mock_post:
        send_change_notification(
            SAMPLE_CHANGES, api_key="re_test_key", from_email="from@example.com", to_email="to@example.com"
        )

    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert called_kwargs["json"]["from"] == "from@example.com"
    assert called_kwargs["json"]["to"] == ["to@example.com"]
    assert "示例目标" in called_kwargs["json"]["html"]


def test_send_change_notification_raises_notification_error_on_api_error_response():
    mock_response = Mock(status_code=422, text="Invalid from address")

    with patch("src.notifier.requests.post", return_value=mock_response):
        with pytest.raises(NotificationError):
            send_change_notification(
                SAMPLE_CHANGES, api_key="re_test_key", from_email="bad", to_email="to@example.com"
            )


def test_send_change_notification_raises_notification_error_when_no_changes_given():
    with pytest.raises(NotificationError):
        send_change_notification([], api_key="re_test_key", from_email="from@example.com", to_email="to@example.com")


def test_send_change_notification_combines_multiple_changes_into_a_single_email():
    changes = [
        {"target": "目标A", "url": "https://a.example.com", "old_value": "1", "new_value": "2"},
        {"target": "目标B", "url": "https://b.example.com", "old_value": "3", "new_value": "4"},
    ]
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"id": "email-456"}

    with patch("src.notifier.requests.post", return_value=mock_response) as mock_post:
        send_change_notification(changes, api_key="re_test_key", from_email="from@example.com", to_email="to@example.com")

    payload = mock_post.call_args.kwargs["json"]
    assert mock_post.call_count == 1
    assert "目标A" in payload["html"]
    assert "目标B" in payload["html"]
