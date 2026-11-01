import subprocess
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def test_container_copies_browser_assets_before_startup():
    dockerfile = (SERVICE_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY web web" in dockerfile


def test_wheel_configuration_includes_browser_assets():
    pyproject = (SERVICE_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"web" = "vedika_ai/web"' in pyproject


def test_deployment_layout_imports_application(tmp_path):
    for directory in ("src", "templates", "web"):
        source = SERVICE_ROOT / directory
        target = tmp_path / directory
        if source.is_dir():
            import shutil

            shutil.copytree(source, target)

    result = subprocess.run(
        [sys.executable, "-c", "from vedika_ai.main import app; assert app"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(tmp_path / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
