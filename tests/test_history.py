from __future__ import annotations

import json
import sqlite3

from codex_hybrid_switcher import history


def write_history_config(tmp_path):
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"codex_home": str(codex_home), "providers": []}), encoding="utf-8")
    db = codex_home / "state_5.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("create table threads (id text primary key, model_provider text, model text)")
        con.execute("insert into threads values ('one', 'openai', 'gpt-5.5')")
        con.execute("insert into threads values ('two', 'openai', 'gpt-5.5')")
        con.execute("insert into threads values ('three', 'custom', 'gpt-5.4')")
    sessions = codex_home / "sessions" / "2026" / "07" / "02"
    sessions.mkdir(parents=True)
    (sessions / "rollout-one.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "session_meta", "payload": {"id": "one", "model_provider": "openai"}}),
                json.dumps(
                    {
                        "type": "turn_context",
                        "payload": {
                            "model": "gpt-5.5",
                            "collaboration_mode": {"settings": {"model": "gpt-5.5"}},
                        },
                    }
                ),
                json.dumps({"type": "event_msg", "payload": {"type": "token_count", "model": "gpt-5.5"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (sessions / "rollout-three.jsonl").write_text(
        json.dumps({"type": "session_meta", "payload": {"id": "three", "model_provider": "custom"}}) + "\n",
        encoding="utf-8",
    )
    return config_path, db


def provider_counts(db):
    with sqlite3.connect(db) as con:
        return dict(con.execute("select model_provider, count(*) from threads group by model_provider"))


def provider_model_counts(db):
    with sqlite3.connect(db) as con:
        return {
            (provider, model): count
            for provider, model, count in con.execute(
                "select model_provider, model, count(*) from threads group by model_provider, model"
            )
        }


def session_lines(db, name="rollout-one.jsonl"):
    path = db.parent / "sessions" / "2026" / "07" / "02" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_history_status_prints_provider_buckets(tmp_path, capsys):
    config_path, _db = write_history_config(tmp_path)

    assert history.run_history_status(str(config_path)) == 0

    out = capsys.readouterr().out
    assert "openai: 2" in out
    assert "custom: 1" in out
    assert "openai/gpt-5.5: 2" in out
    assert "custom/gpt-5.4: 1" in out
    assert "Session files with openai metadata: 1" in out


def test_unify_history_dry_run_does_not_change_database(tmp_path, capsys):
    config_path, db = write_history_config(tmp_path)

    assert history.run_unify_history(str(config_path), dry_run=True) == 0

    assert provider_counts(db) == {"custom": 1, "openai": 2}
    assert provider_model_counts(db) == {("custom", "gpt-5.4"): 1, ("openai", "gpt-5.5"): 2}
    assert not list(db.parent.glob("state_5.sqlite.bak-codex-hybrid-*"))
    assert not list((db.parent / "sessions" / "2026" / "07" / "02").glob("*.bak-codex-hybrid-*"))
    assert session_lines(db)[0]["payload"]["model_provider"] == "openai"
    assert "Dry run" in capsys.readouterr().out


def test_unify_history_apply_backs_up_and_migrates(tmp_path, monkeypatch, capsys):
    config_path, db = write_history_config(tmp_path)
    monkeypatch.setattr(history, "codex_is_running", lambda: False)

    assert history.run_unify_history(str(config_path), dry_run=False, apply=True) == 0

    assert provider_counts(db) == {"custom": 3}
    assert provider_model_counts(db) == {("custom", "gpt-5.4"): 1, ("custom", "gpt-5.5"): 2}
    backups = list(db.parent.glob("state_5.sqlite.bak-codex-hybrid-*"))
    assert len(backups) == 1
    lines = session_lines(db)
    assert lines[0]["payload"]["model_provider"] == "custom"
    assert lines[1]["payload"]["model"] == "gpt-5.5"
    session_backups = list((db.parent / "sessions" / "2026" / "07" / "02").glob("rollout-one.jsonl.bak-codex-hybrid-*"))
    assert len(session_backups) == 1
    out = capsys.readouterr().out
    assert "Backed up previous state database" in out
    assert "Backed up previous session file" in out
    assert "custom: 3" in out


def test_unify_history_apply_can_migrate_provider_and_model(tmp_path, monkeypatch, capsys):
    config_path, db = write_history_config(tmp_path)
    monkeypatch.setattr(history, "codex_is_running", lambda: False)

    assert (
        history.run_unify_history(
            str(config_path),
            from_provider="openai",
            to_provider="custom",
            to_model="gpt-5.4",
            dry_run=False,
            apply=True,
        )
        == 0
    )

    assert provider_counts(db) == {"custom": 3}
    assert provider_model_counts(db) == {("custom", "gpt-5.4"): 3}
    lines = session_lines(db)
    assert lines[0]["payload"]["model_provider"] == "custom"
    assert lines[1]["payload"]["model"] == "gpt-5.4"
    assert lines[1]["payload"]["collaboration_mode"]["settings"]["model"] == "gpt-5.4"
    assert lines[2]["payload"]["model"] == "gpt-5.5"
    out = capsys.readouterr().out
    assert "Model rows to migrate: 2" in out
    assert "Session files to migrate: 1" in out
    assert "custom/gpt-5.4: 3" in out


def test_restore_history_backup_replaces_database(tmp_path, monkeypatch):
    config_path, db = write_history_config(tmp_path)
    monkeypatch.setattr(history, "codex_is_running", lambda: False)
    assert history.run_unify_history(str(config_path), dry_run=False, apply=True) == 0
    backup = next(db.parent.glob("state_5.sqlite.bak-codex-hybrid-*"))

    assert history.run_restore_history_backup(str(config_path), backup=str(backup)) == 0

    assert provider_counts(db) == {"custom": 1, "openai": 2}
    assert len(list(db.parent.glob("state_5.sqlite.bak-codex-hybrid-*"))) >= 2
