from scripts import handoff


def test_preflight_is_machine_readable(monkeypatch):
    monkeypatch.setattr(
        handoff,
        "_command_version",
        lambda command: {"available": True, "version": "test", "error": None},
    )
    report = handoff.collect_preflight()
    assert report["schema_version"] == "1.0"
    assert report["checks"]["compose_file"] is True
    assert report["demo_ready"] is True
    assert "fixture UI/API" in report["scope"]


def test_smoke_checks_user_and_developer_entrypoints(monkeypatch):
    monkeypatch.setattr(
        handoff,
        "_fetch",
        lambda base_url, path, timeout=8: {"url": base_url + path, "ok": True, "status": 200},
    )
    report = handoff.smoke("http://local")
    assert report["passed"] is True
    checked = {item["url"] for item in report["checks"]}
    assert "http://local/" in checked
    assert "http://local/docs" in checked
    assert "http://local/system/operations" in checked
