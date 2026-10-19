from scripts.build_ui_showcase import build


def test_showcase_embeds_all_current_ui_screens_and_live_links(tmp_path):
    screenshots = tmp_path / "screenshots"
    screenshots.mkdir()
    for name in ("dashboard.png", "intake.png", "workbench.png"):
        (screenshots / name).write_bytes(b"fake-png")

    output = build(screenshots, tmp_path / "showcase.html")
    html = output.read_text(encoding="utf-8")

    assert html.count("data:image/png;base64,") == 3
    assert "1 · Dashboard" in html
    assert "2 · Nạp hồ sơ" in html
    assert "3 · Workbench" in html
    assert "http://127.0.0.1:8000/?view=dashboard" in html
    assert "http://127.0.0.1:8000/?view=intake" in html
    assert "http://127.0.0.1:8000/?view=workbench" in html
    assert "prototype/insurance_review_console_v2.html" not in html
