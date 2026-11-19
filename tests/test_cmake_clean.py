from pathlib import Path

import pytest
from py_app_dev.core.exceptions import UserNotificationException
from yanga_core.domain.components import Component
from yanga_core.domain.execution_context import ExecutionContext

from yanga.cmake.builder import CMakeBuildSystemGenerator
from yanga.cmake.clean import ComponentCleanCMakeGenerator
from yanga.cmake.cmake_backend import CMakeAddExecutable, CMakeAddLibrary, CMakeCustomTarget, CMakeElement


def _clean_targets(elements: list[CMakeElement]) -> list[CMakeCustomTarget]:
    return [element for element in elements if isinstance(element, CMakeCustomTarget) and element.name.endswith("_clean")]


def test_one_clean_target_per_component_emitted_via_builder(execution_context: ExecutionContext, output_dir: Path) -> None:
    execution_context.platform = None
    cmake_file = CMakeBuildSystemGenerator(execution_context, output_dir).create_variant_cmake_file()

    assert {target.name for target in _clean_targets(cmake_file.content)} == {"CompA_clean", "CompBNotTestable_clean"}


def test_clean_target_with_no_tagged_targets_only_wipes_component_build_dir(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ComponentCleanCMakeGenerator(execution_context, output_dir).generate()

    [comp_a_clean] = [target for target in _clean_targets(elements) if target.name == "CompA_clean"]
    rendered = comp_a_clean.to_string()
    assert "DEPENDS" not in rendered
    assert "ADDITIONAL_CLEAN_FILES" not in rendered
    assert [command.to_string() for command in comp_a_clean.commands] == ["COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_BUILD_DIR}/CompA"]


def test_clean_target_includes_tagged_lib_and_executable_intermediate_dirs(execution_context: ExecutionContext, output_dir: Path) -> None:
    existing_elements: list[CMakeElement] = [
        CMakeAddLibrary("CompA", files=[Path("a.cpp")], component_name="CompA"),
        CMakeAddExecutable(name="CompA", sources=[], component_name="CompA"),
    ]

    elements = ComponentCleanCMakeGenerator(execution_context, output_dir, existing_elements=existing_elements).generate()

    [comp_a_clean] = [target for target in _clean_targets(elements) if target.name == "CompA_clean"]
    rendered_commands = [command.to_string() for command in comp_a_clean.commands]
    assert rendered_commands == [
        "COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_BUILD_DIR}/CompA",
        "COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_BUILD_DIR}/CMakeFiles/CompA_lib.dir",
        "COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_BUILD_DIR}/CMakeFiles/CompA.dir",
    ]


def test_clean_target_emits_no_target_genex_to_avoid_implicit_build_deps(execution_context: ExecutionContext, output_dir: Path) -> None:
    """
    Regression: target-based generator expressions in add_custom_target COMMANDs imply build-order dependencies.

    A clean target that uses ``$<TARGET_FILE:tgt>`` (or any other ``$<TARGET_*:>`` form) makes
    the clean target depend on the very thing it intends to delete, so the build runs to
    completion before the rm executes — defeating the point of clean.
    """
    existing_elements: list[CMakeElement] = [
        CMakeAddLibrary("CompA", files=[Path("a.cpp")], component_name="CompA"),
        CMakeAddExecutable(name="CompA", sources=[], component_name="CompA"),
    ]

    elements = ComponentCleanCMakeGenerator(execution_context, output_dir, existing_elements=existing_elements).generate()

    for clean_target in _clean_targets(elements):
        for command in clean_target.commands:
            rendered = command.to_string()
            assert "$<TARGET_" not in rendered, f"Clean target {clean_target.name!r} uses target genex which implies a build dependency: {rendered}"


def test_clean_target_ignores_untagged_targets_and_other_components(execution_context: ExecutionContext, output_dir: Path) -> None:
    existing_elements: list[CMakeElement] = [
        CMakeAddLibrary("Untagged", files=[Path("u.cpp")]),
        CMakeAddExecutable(name="OtherComp_test", sources=[], component_name="OtherComp"),
    ]

    elements = ComponentCleanCMakeGenerator(execution_context, output_dir, existing_elements=existing_elements).generate()

    [comp_a_clean] = [target for target in _clean_targets(elements) if target.name == "CompA_clean"]
    assert [command.to_string() for command in comp_a_clean.commands] == ["COMMAND ${CMAKE_COMMAND} -E rm -rf ${CMAKE_BUILD_DIR}/CompA"]


@pytest.mark.parametrize("bad_name", ["../escape", "..", "/absolute/escape", ".", "./"])
def test_rejects_component_names_resolving_to_or_escaping_build_root(bad_name: str, execution_context: ExecutionContext, output_dir: Path) -> None:
    # Override the mock's read-only components; only the (bad) name matters here.
    execution_context.components = [  # type: ignore[misc]
        Component(name=bad_name, path=Path("evil"), sources=[Path("evil.cpp")], testing=[]),
    ]

    with pytest.raises(UserNotificationException, match="resolves to or escapes cmake build root"):
        ComponentCleanCMakeGenerator(execution_context, output_dir).generate()
