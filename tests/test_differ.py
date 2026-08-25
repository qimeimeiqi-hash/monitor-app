from src.differ import compare_content, compute_hash


def test_compare_content_reports_no_change_when_content_matches_previous_snapshot():
    content = "价格：100元"
    previous_snapshot = {"content": content, "content_hash": compute_hash(content)}

    result = compare_content(content, previous_snapshot)

    assert result.changed is False
    assert result.old_value == content
    assert result.new_value == content


def test_compare_content_reports_change_when_content_differs_from_previous_snapshot():
    old_content = "价格：100元"
    new_content = "价格：120元"
    previous_snapshot = {"content": old_content, "content_hash": compute_hash(old_content)}

    result = compare_content(new_content, previous_snapshot)

    assert result.changed is True
    assert result.old_value == old_content
    assert result.new_value == new_content


def test_compare_content_treats_first_run_without_snapshot_as_baseline_not_a_change():
    result = compare_content("首次抓取内容", previous_snapshot=None)

    assert result.changed is False
    assert result.old_value is None
    assert result.new_value == "首次抓取内容"
