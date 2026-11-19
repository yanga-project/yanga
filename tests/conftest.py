import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from py_app_dev.core.data_registry import DataRegistry
from yanga_core.domain.component_resolver import ComponentResolver
from yanga_core.domain.config import ComponentConfig, TestingBlockConfig
from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.spl_paths import SPLPaths

from tests.utils import this_repository_root_dir
from yanga.kickstart.create import KickstartProject


@pytest.fixture
def locate_artifact():
    """Fixture to mock the locate_artifact method."""
    with patch(
        SPLPaths.__module__ + "." + SPLPaths.__name__ + ".locate_artifact",
        side_effect=lambda file, _: Path(file),
    ) as my_locate_artifact:
        yield my_locate_artifact


@pytest.fixture
def execution_context(tmp_path: Path) -> ExecutionContext:
    # Declared component configs; the resolver turns them into resolved Components.
    return make_execution_context(
        tmp_path,
        [
            ComponentConfig(
                name="CompA",
                path=Path("compA"),
                sources=["compA_source.cpp"],
                testing=[TestingBlockConfig(framework="gtest", sources=["test_compA_source.cpp"])],
            ),
            ComponentConfig(
                name="CompBNotTestable",
                path=Path("compB"),
                sources=["compB_source.cpp"],
                testing=[],
            ),
        ],
    )


@pytest.fixture
def container_execution_context(tmp_path: Path) -> ExecutionContext:
    """A variant selecting container ``group``, which holds container ``net``, which holds ``tcp`` (gtest tests) and ``udp`` (tessy tests)."""
    configs = [
        ComponentConfig(name="group", subcomponents=["net"]),
        ComponentConfig(name="net", subcomponents=["tcp", "udp"]),
        ComponentConfig(name="tcp", path=Path("tcp"), sources=["tcp.cpp"], testing=[TestingBlockConfig(framework="gtest", sources=["test_tcp.cpp"])]),
        ComponentConfig(name="udp", path=Path("udp"), sources=["udp.cpp"], testing=[TestingBlockConfig(framework="tessy", sources=["test_udp.c"])]),
    ]
    return make_execution_context(tmp_path, configs, ["group"])


def make_execution_context(tmp_path: Path, configs: list[ComponentConfig], selected_names: list[str] | None = None) -> ExecutionContext:
    spl_paths = SPLPaths(tmp_path, "mock_variant", "mock_platform", "mock_build_type", create_yanga_build_dir=True)
    resolver = ComponentResolver(configs, selected_names or [config.name for config in configs], spl_paths)
    env = Mock(spec=ExecutionContext)
    env.project_root_dir = tmp_path
    env.variant_name = "mock_variant"
    env.spl_paths = spl_paths
    env.data_registry = DataRegistry()
    # The resolver is the single component authority; the context's components are the
    # resolved components it builds (the whole declared set unless names are given).
    env.component_resolver = resolver
    env.components = resolver.selected_components
    env.project_configs = []
    env.variant = None
    env.variant_testing = []
    return env


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def get_test_data_path():
    """Fixture that returns a function to get test data file paths by name."""

    def _get_test_data_path(filename: str) -> Path:
        """Get path to a test data file by filename."""
        return Path(__file__).parent / "data" / filename

    return _get_test_data_path


@pytest.fixture
def mini_project(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    # The project pipeline spawns python subprocesses (e.g. pypeline's bootstrap) with this
    # venv's python. They must not inherit pytest-cov's instrumentation: they would write
    # statement-mode .coverage.* files that cannot be combined with the branch coverage data.
    for env_var in ("COVERAGE_PROCESS_START", "COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE"):
        monkeypatch.delenv(env_var, raising=False)
    # Create temp directory in the repository to ensure same drive as yanga source
    # This avoids cross-drive path issues on Windows with Poetry
    test_name = request.node.name
    tests_dir = this_repository_root_dir() / "build" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    project_dir = Path(tempfile.mkdtemp(prefix=f"{test_name}_", dir=tests_dir))

    try:
        # Create example project
        KickstartProject(project_dir).run()
        assert project_dir.joinpath("yanga.yaml").exists()

        # Replace the YANGA dependency in the pyproject.toml
        pyproject_toml = project_dir.joinpath("pyproject.toml")
        new_dependency = f"yanga @ file:///{this_repository_root_dir().as_posix()}"
        pyproject_toml.write_text(pyproject_toml.read_text().replace("yanga>=2,<3", new_dependency))

        assert '"yanga @ file:///' in pyproject_toml.read_text(), "Failed to set the local yanga dependency in the mini project."

        # Use the python version running the tests; the CI runners only have the matrix python installed
        yanga_yaml = project_dir.joinpath("yanga.yaml")
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        yanga_yaml.write_text(yanga_yaml.read_text().replace('python_version: "3.11"', f'python_version: "{python_version}"'))

        assert f'python_version: "{python_version}"' in yanga_yaml.read_text(), "Failed to set the python version in the mini project."

        yield project_dir
    finally:
        # Cleanup: remove the test project directory
        if project_dir.exists():
            pass  # shutil.rmtree(project_dir, ignore_errors=True)
