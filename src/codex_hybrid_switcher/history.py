from __future__ import annotations

import json
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .switcher import codex_is_running


def state_db_path(config_path: str | None = None) -> Path:
    config = load_config(config_path)
    return config.codex_home / "state_5.sqlite"


@dataclass
class SessionMigration:
    path: Path
    provider_changed: bool = False
    model_changed: bool = False


def threads_columns(db: Path) -> set[str]:
    if not db.exists():
        raise FileNotFoundError(f"state database not found: {db}")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        tables = {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
        if "threads" not in tables:
            raise RuntimeError("state database does not contain a threads table")
        return {row[1] for row in con.execute("pragma table_info(threads)")}


def require_threads_columns(db: Path, required: set[str] | None = None) -> None:
    columns = threads_columns(db)
    missing = (required or {"model_provider"}) - columns
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(f"threads table does not contain required column(s): {missing_list}")


def provider_counts(db: Path) -> list[tuple[str | None, int]]:
    require_threads_columns(db, {"model_provider"})
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        return list(
            con.execute(
                "select model_provider, count(*) from threads group by model_provider order by count(*) desc, model_provider"
            )
        )


def provider_model_counts(db: Path) -> list[tuple[str | None, str | None, int]]:
    require_threads_columns(db, {"model_provider", "model"})
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        return list(
            con.execute(
                """
                select model_provider, model, count(*)
                from threads
                group by model_provider, model
                order by count(*) desc, model_provider, model
                """
            )
        )


def thread_count_for_provider(db: Path, provider: str) -> int:
    require_threads_columns(db, {"model_provider"})
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        row = con.execute("select count(*) from threads where model_provider = ?", (provider,)).fetchone()
    return int(row[0] if row else 0)


def thread_count_for_provider_model(db: Path, provider: str, *, from_model: str | None, to_model: str) -> int:
    require_threads_columns(db, {"model_provider", "model"})
    sql = "select count(*) from threads where model_provider = ? and model is not ?"
    params: list[str] = [provider, to_model]
    if from_model:
        sql += " and model = ?"
        params.append(from_model)
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        row = con.execute(sql, params).fetchone()
    return int(row[0] if row else 0)


def backup_sqlite(db: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = db.with_name(f"{db.name}.bak-codex-hybrid-{stamp}")
    counter = 1
    while backup.exists():
        backup = db.with_name(f"{db.name}.bak-codex-hybrid-{stamp}-{counter}")
        counter += 1
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as source:
        with sqlite3.connect(backup) as target:
            source.backup(target)
    return backup


def backup_regular_file(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-codex-hybrid-{stamp}")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak-codex-hybrid-{stamp}-{counter}")
        counter += 1
    shutil.copy2(path, backup)
    return backup


def print_counts(counts: list[tuple[str | None, int]]) -> None:
    if not counts:
        print("  - <none>: 0")
        return
    for provider, count in counts:
        print(f"  - {provider or '<null>'}: {count}")


def print_model_counts(counts: list[tuple[str | None, str | None, int]]) -> None:
    if not counts:
        print("  - <none>/<none>: 0")
        return
    for provider, model, count in counts:
        print(f"  - {provider or '<null>'}/{model or '<null>'}: {count}")


def _change_model_field(payload: dict, *, from_model: str | None, to_model: str) -> bool:
    if "model" not in payload:
        return False
    if payload.get("model") == to_model:
        return False
    if from_model and payload.get("model") != from_model:
        return False
    payload["model"] = to_model
    return True


def _change_collaboration_model(payload: dict, *, from_model: str | None, to_model: str) -> bool:
    collaboration = payload.get("collaboration_mode")
    if not isinstance(collaboration, dict):
        return False
    settings = collaboration.get("settings")
    if not isinstance(settings, dict):
        return False
    if settings.get("model") == to_model:
        return False
    if from_model and settings.get("model") != from_model:
        return False
    settings["model"] = to_model
    return True


def planned_session_migration(
    path: Path,
    *,
    from_provider: str,
    to_provider: str,
    from_model: str | None,
    to_model: str | None,
) -> SessionMigration | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return None

    first_provider_matches = False
    provider_changed = False
    try:
        first = json.loads(lines[0])
    except json.JSONDecodeError:
        return None
    if first.get("type") == "session_meta":
        payload = first.get("payload")
        if isinstance(payload, dict) and payload.get("model_provider") == from_provider:
            first_provider_matches = True
            if from_provider != to_provider:
                provider_changed = True
    if not first_provider_matches:
        return None

    model_changed = False
    if to_model:
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue
            if obj.get("type") in {"session_meta", "turn_context"}:
                would_change_model = payload.get("model") != to_model and (not from_model or payload.get("model") == from_model)
                model_changed = model_changed or would_change_model
            if obj.get("type") == "turn_context":
                collaboration = payload.get("collaboration_mode")
                settings = collaboration.get("settings") if isinstance(collaboration, dict) else None
                if isinstance(settings, dict):
                    would_change_settings = settings.get("model") != to_model and (
                        not from_model or settings.get("model") == from_model
                    )
                    model_changed = model_changed or would_change_settings

    if not provider_changed and not model_changed:
        return None
    return SessionMigration(path=path, provider_changed=provider_changed, model_changed=model_changed)


def planned_session_migrations(
    codex_home: Path,
    *,
    from_provider: str,
    to_provider: str,
    from_model: str | None,
    to_model: str | None,
) -> list[SessionMigration]:
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        return []
    migrations: list[SessionMigration] = []
    for path in sorted(sessions_dir.rglob("*.jsonl")):
        migration = planned_session_migration(
            path,
            from_provider=from_provider,
            to_provider=to_provider,
            from_model=from_model,
            to_model=to_model,
        )
        if migration:
            migrations.append(migration)
    return migrations


def apply_session_migration(
    migration: SessionMigration,
    *,
    from_provider: str,
    to_provider: str,
    from_model: str | None,
    to_model: str | None,
) -> Path:
    lines = migration.path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    for index, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        payload = obj.get("payload")
        changed = False
        if index == 0 and obj.get("type") == "session_meta" and isinstance(payload, dict):
            if payload.get("model_provider") == from_provider:
                payload["model_provider"] = to_provider
                changed = True
            if to_model:
                changed = _change_model_field(payload, from_model=from_model, to_model=to_model) or changed
        elif obj.get("type") == "turn_context" and isinstance(payload, dict) and to_model:
            changed = _change_model_field(payload, from_model=from_model, to_model=to_model) or changed
            changed = _change_collaboration_model(payload, from_model=from_model, to_model=to_model) or changed
        if changed:
            new_lines.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        else:
            new_lines.append(line)
    backup = backup_regular_file(migration.path)
    migration.path.write_text("\n".join(new_lines) + ("\n" if lines else ""), encoding="utf-8")
    return backup


def run_history_status(config_path: str | None = None) -> int:
    db = state_db_path(config_path)
    print("Codex history provider buckets")
    print(f"state_db: {db}")
    try:
        counts = provider_counts(db)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print_counts(counts)
    try:
        model_counts = provider_model_counts(db)
    except Exception:
        return 0
    print("Provider/model buckets")
    print_model_counts(model_counts)
    migrations = planned_session_migrations(
        db.parent,
        from_provider="openai",
        to_provider="custom",
        from_model=None,
        to_model=None,
    )
    if migrations:
        print(f"Session files with openai metadata: {len(migrations)}")
    return 0


def run_unify_history(
    config_path: str | None = None,
    *,
    from_provider: str = "openai",
    to_provider: str = "custom",
    from_model: str | None = None,
    to_model: str | None = None,
    dry_run: bool = True,
    apply: bool = False,
) -> int:
    db = state_db_path(config_path)
    codex_home = db.parent
    print("Codex history unify")
    print(f"state_db: {db}")
    print(f"from_provider: {from_provider}")
    print(f"to_provider: {to_provider}")
    if from_model:
        print(f"from_model: {from_model}")
    if to_model:
        print(f"to_model: {to_model}")
    try:
        before = provider_counts(db)
        migrate_count = thread_count_for_provider(db, from_provider)
        model_migrate_count = (
            thread_count_for_provider_model(db, from_provider, from_model=from_model, to_model=to_model)
            if to_model
            else 0
        )
        session_migrations = planned_session_migrations(
            codex_home,
            from_provider=from_provider,
            to_provider=to_provider,
            from_model=from_model,
            to_model=to_model,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Provider buckets before:")
    print_counts(before)
    if to_model:
        try:
            print("Provider/model buckets before:")
            print_model_counts(provider_model_counts(db))
        except Exception:
            pass
    print(f"Provider rows to migrate: {migrate_count}")
    if to_model:
        print(f"Model rows to migrate: {model_migrate_count}")
    print(f"Session files to migrate: {len(session_migrations)}")
    for migration in session_migrations[:10]:
        changes = []
        if migration.provider_changed:
            changes.append("provider")
        if migration.model_changed:
            changes.append("model")
        print(f"  - {migration.path} ({', '.join(changes)})")
    if len(session_migrations) > 10:
        print(f"  - ... {len(session_migrations) - 10} more")

    if not apply or dry_run:
        print("Dry run: no history or session files were changed and no backup was created.")
        return 0

    if codex_is_running():
        print("Codex Desktop appears to be running. Quit Codex completely before rewriting history buckets.")
        return 2

    backup = backup_sqlite(db)
    session_backups = [
        apply_session_migration(
            migration,
            from_provider=from_provider,
            to_provider=to_provider,
            from_model=from_model,
            to_model=to_model,
        )
        for migration in session_migrations
    ]
    with sqlite3.connect(db) as con:
        if to_model:
            sql = "update threads set model_provider = ?, model = ? where model_provider = ?"
            params: list[str] = [to_provider, to_model, from_provider]
            if from_model:
                sql += " and model = ?"
                params.append(from_model)
            con.execute(sql, params)
        else:
            con.execute("update threads set model_provider = ? where model_provider = ?", (to_provider, from_provider))
        con.commit()

    after = provider_counts(db)
    print(f"Backed up previous state database: {backup}")
    for session_backup in session_backups:
        print(f"Backed up previous session file: {session_backup}")
    print("Provider buckets after:")
    print_counts(after)
    if to_model:
        try:
            print("Provider/model buckets after:")
            print_model_counts(provider_model_counts(db))
        except Exception:
            pass
    return 0


def run_restore_history_backup(config_path: str | None = None, *, backup: str | None = None) -> int:
    if not backup:
        print("--backup is required.")
        return 2
    db = state_db_path(config_path)
    backup_path = Path(backup).expanduser()
    if not backup_path.exists():
        print(f"backup not found: {backup_path}")
        return 2
    if codex_is_running():
        print("Codex Desktop appears to be running. Quit Codex completely before restoring history.")
        return 2
    current_backup = backup_sqlite(db)
    shutil.copy2(backup_path, db)
    print(f"Backed up current state database before restore: {current_backup}")
    print(f"Restored history database from: {backup_path}")
    return 0
