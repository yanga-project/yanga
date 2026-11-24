import os
import sys
from pathlib import Path

import pytest
from py_app_dev.core.subprocess import SubprocessExecutor

C_SOURCE = "int add(int a, int b) { return a + b; }\n"
TEST_SOURCE = """import ctypes
from pathlib import Path


def test_add() -> None:
    assert ctypes.CDLL(str(Path(__file__).parent / "{library}")).add(1, 2) == 3
"""
PYTEST_COV_VARIABLES = ("COVERAGE_PROCESS_START", "COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE")


@pytest.mark.parametrize(
    "compiler",
    [
        "clang",
        pytest.param("gcc", marks=pytest.mark.skipif(sys.platform != "linux", reason="gcc is only used on Linux")),
    ],
)
def test_gcov_data_is_written_when_pytest_exits(compiler: str, tmp_path: Path) -> None:
    suffix = {"win32": ".dll", "darwin": ".dylib"}.get(sys.platform, ".so")
    c_file = tmp_path / "add.c"
    c_file.write_text(C_SOURCE)
    library = tmp_path / f"libadd{suffix}"
    SubprocessExecutor([compiler, "--coverage", "-shared", "-fPIC", c_file, "-o", library], print_output=False).execute()
    test_file = tmp_path / "test_add.py"
    test_file.write_text(TEST_SOURCE.format(library=library.name))
    env = {key: value for key, value in os.environ.items() if key not in PYTEST_COV_VARIABLES}

    result = SubprocessExecutor(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", test_file],
        cwd=tmp_path,
        env=env,
        print_output=False,
    ).execute(handle_errors=False)

    assert result
    assert result.returncode == 0
    assert list(tmp_path.rglob("*.gcda"))
