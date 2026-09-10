"""alembic 마이그레이션이 현재 모델과 일치하는지 검증한다."""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _alembic(args, db_path):
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "AUTO_CREATE_TABLES": "false",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )


def test_upgrade_then_no_drift(tmp_path):
    db = tmp_path / "m.db"

    up = _alembic(["upgrade", "head"], db)
    assert up.returncode == 0, up.stdout + up.stderr

    check = _alembic(["check"], db)
    assert check.returncode == 0, (
        "모델과 마이그레이션이 어긋납니다. "
        "`alembic revision --autogenerate` 로 리비전을 추가하세요.\n"
        + check.stdout
        + check.stderr
    )


def test_downgrade_to_base(tmp_path):
    db = tmp_path / "m.db"
    assert _alembic(["upgrade", "head"], db).returncode == 0
    down = _alembic(["downgrade", "base"], db)
    assert down.returncode == 0, down.stdout + down.stderr
