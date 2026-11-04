import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from clanguru.doc_generator import MarkdownFormatter
from yanga_core.domain.execution_context import ExecutionContext, UserVariantRequest

from yanga.cmake.builder import CMakeBuildSystemGenerator
from yanga.cmake.cmake_backend import CMakeAddExecutable, CMakeAddLibrary, CMakeCustomTarget
from yanga.cmake.generator import CMakeFile
from yanga.cmake.targets import TargetsData
from yanga.commands.targets import TargetDependencyTreeBuilder, TargetTreeNode, create_doc_structure


@dataclass
class MissingPath:
    previous: str
    current: str
    actual_children: list[str]

    def __str__(self) -> str:
        return f"MissingPath(previous='{self.previous}', current='{self.current}', actual_children={self.actual_children})"


def check_target_tree_path(node: TargetTreeNode, path: list[str]) -> MissingPath | None:
    """
    Helper function to check if a path exists in the target tree.

    If the first element in the path does not match any of the current node's children,
    it shall return the missing path (previousNode, currentNode).

    It shall return the missing path (NodeA, NodeB) if it does not exist or None if everything is fine.
    """
    if not path:
        return None

    current_name = path[0]
    for child in node.children:
        if child.target.name == current_name or child.target.description == current_name:
            return check_target_tree_path(child, path[1:])

    # If we reach here, the current_name was not found among the children
    actual_children = [child.target.name for child in node.children]
    return MissingPath(previous=node.target.name, current=current_name, actual_children=actual_children)


def test_dependency_tree_builder(get_test_data_path: Callable[[str], Path]) -> None:
    targets_data = TargetsData.from_json_file(get_test_data_path("sample_targets_data.json"))
    tree_builder = TargetDependencyTreeBuilder(targets_data)
    assert tree_builder
    target_tree = tree_builder.generate_target_tree("report")
    assert target_tree

    missing_path = check_target_tree_path(
        target_tree,
        [
            "results",
            "light_controller_results",
            "light_controller_coverage",
            "Generate coverage report for component light_controller",
            "Run the test executable, generate JUnit report and return success independent of the test result",
            "light_controller",
            "light_controller_PC_lib",
        ],
    )
    assert missing_path is None, f"Missing path in target tree: {missing_path}"

    missing_path = check_target_tree_path(
        target_tree,
        [
            "results",
            "light_controller_results",
            "light_controller_coverage",
            "Generate coverage report for component light_controller",
            "Run the test executable, generate JUnit report and return success independent of the test result",
            "light_controller",
            "Run clanguru to generate mockup sources",
            "Create partial link library containing only the productive sources",
            "light_controller_PC_lib",
        ],
    )
    assert missing_path is None, f"Missing path in target tree: {missing_path}"


def test_target_dependency_html_builder(get_test_data_path: Callable[[str], Path]) -> None:
    targets_data = TargetsData.from_json_file(get_test_data_path("sample_targets_data.json"))
    content = MarkdownFormatter().format(create_doc_structure(targets_data, ["report"]))
    assert content


def test_create_target_dependencies_file():
    with TemporaryDirectory() as temp_dir:
        project_root_dir = Path(temp_dir)
        output_dir = project_root_dir / "output"

        execution_context = ExecutionContext(
            project_root_dir=project_root_dir,
            user_request=UserVariantRequest("test_variant"),
            variant_name="test_variant",
        )

        generator = CMakeBuildSystemGenerator(execution_context, output_dir)

        cmake_file1 = CMakeFile(Path("test1.cmake"))
        cmake_file1.append(CMakeCustomTarget(name="test_target", description="Test custom target", commands=[], depends=["dependency1", "dependency2"]))
        cmake_file1.append(CMakeAddExecutable(name="test_exe", sources=["main.cpp"], libraries=["lib1", "lib2"]))

        cmake_file2 = CMakeFile(Path("test2.cmake"))
        cmake_file2.append(CMakeAddLibrary("test_lib", [Path("source1.cpp"), Path("source2.cpp")]))

        cmake_files = [cmake_file1, cmake_file2]

        result_file = generator.create_target_dependencies_file(cmake_files)

        generated_json = result_file.to_string()
        targets_data = TargetsData.from_dict(json.loads(generated_json))

        assert len(targets_data.targets) == 3

        custom_target = next(t for t in targets_data.targets if t.name == "test_target")
        assert custom_target.description == "Test custom target"
        assert custom_target.depends == ["dependency1", "dependency2"]
        assert custom_target.target_type.to_string() == "CUSTOM_TARGET"

        exe_target = next(t for t in targets_data.targets if t.name == "test_exe")
        assert exe_target.description == "Executable target: test_exe"
        assert exe_target.depends == ["lib1", "lib2", "main.cpp"]
        assert exe_target.outputs == ["test_exe"]
        assert exe_target.target_type.to_string() == "EXECUTABLE"

        lib_target = next(t for t in targets_data.targets if t.name == "test_lib_lib")
        assert lib_target.description == "Object library: test_lib"
        assert lib_target.depends == ["source1.cpp", "source2.cpp"]
        assert lib_target.outputs == ["test_lib_lib"]
        assert lib_target.target_type.to_string() == "OBJECT_LIBRARY"
