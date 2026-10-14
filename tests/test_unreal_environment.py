from scripts.check_unreal_environment import _inspect_epic_entitlement


def _write_launcher_log(tmp_path, text):
    log_root = tmp_path / "EpicGamesLauncher" / "Saved" / "Logs"
    log_root.mkdir(parents=True)
    (log_root / "EpicGamesLauncher.log").write_text(text, encoding="utf-8")


def test_detects_zero_epic_entitlements_without_account_data(monkeypatch, tmp_path):
    _write_launcher_log(
        tmp_path,
        "\n".join(
            [
                "LogCommunityPortalAppManager: EoshState = WaitingForBuildsAndItemFiles",
                "LogCommunityPortalAppManager: LoadItemFiles: Loaded 0 item files in 0.0 secs",
                "LogCommunityPortalOSS: Display: ...found 0 entitled apps",
            ]
        ),
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    result = _inspect_epic_entitlement()

    assert result == {
        "status": "ZERO_ENTITLEMENTS",
        "reason": "Launcher received no UE item files or entitled apps",
        "latest_log": "EpicGamesLauncher.log",
    }


def test_reports_positive_entitlement_count(monkeypatch, tmp_path):
    _write_launcher_log(
        tmp_path,
        "LogCommunityPortalOSS: Display: ...found 3 entitled apps",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    result = _inspect_epic_entitlement()

    assert result["status"] == "ENTITLEMENTS_PRESENT"
    assert result["reason"] == "Launcher reported 3 entitled apps"
