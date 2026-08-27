from unittest.mock import Mock, patch

import pytest

from src.notifier import NotificationError, send_change_notification, send_signal_notification

SAMPLE_CHANGES = [
    {"target": "示例目标", "url": "https://example.com", "old_value": "旧", "new_value": "新"},
]

SAMPLE_SIGNALS = [
    {
        "target": "伊藤忠商事",
        "url": "https://finance.yahoo.com/quote/8001.T",
        "action": "buy",
        "price_label": "JPY 1234.5（2026-08-25 終値）",
        "reasons": ["安値圏で鎚子線が出現（下値支持が強い）"],
        "stop_loss_label": "JPY 1200.0",
    },
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


def test_send_signal_notification_posts_expected_payload_with_action_and_reasons():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"id": "email-789"}

    with patch("src.notifier.requests.post", return_value=mock_response) as mock_post:
        send_signal_notification(
            SAMPLE_SIGNALS, api_key="re_test_key", from_email="from@example.com", to_email="to@example.com"
        )

    called_kwargs = mock_post.call_args.kwargs
    payload = called_kwargs["json"]
    assert called_kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert payload["from"] == "from@example.com"
    assert payload["to"] == ["to@example.com"]
    assert "伊藤忠商事" in payload["html"]
    assert "買い" in payload["html"]
    assert "鎚子線" in payload["html"]
    assert "JPY 1200.0" in payload["html"]


def test_send_signal_notification_labels_sell_action_and_omits_missing_stop_loss():
    sell_signal = [
        {
            "target": "三菱商事",
            "url": "https://finance.yahoo.com/quote/8058.T",
            "action": "sell",
            "price_label": "JPY 3000.0（2026-08-25 終値）",
            "reasons": ["高値圏で陰包陽（弱気の包み足）が出現"],
            "stop_loss_label": None,
        }
    ]
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"id": "email-999"}

    with patch("src.notifier.requests.post", return_value=mock_response) as mock_post:
        send_signal_notification(
            sell_signal, api_key="re_test_key", from_email="from@example.com", to_email="to@example.com"
        )

    payload = mock_post.call_args.kwargs["json"]
    assert "売り" in payload["html"]
    assert "損切" not in payload["html"]


def test_send_signal_notification_raises_notification_error_on_api_error_response():
    mock_response = Mock(status_code=422, text="Invalid from address")

    with patch("src.notifier.requests.post", return_value=mock_response):
        with pytest.raises(NotificationError):
            send_signal_notification(
                SAMPLE_SIGNALS, api_key="re_test_key", from_email="bad", to_email="to@example.com"
            )


def test_send_signal_notification_raises_notification_error_when_no_signals_given():
    with pytest.raises(NotificationError):
        send_signal_notification([], api_key="re_test_key", from_email="from@example.com", to_email="to@example.com")
