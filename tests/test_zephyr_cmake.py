from pathlib import Path

from py_app_dev.core.find import find_elements_of_type
from yanga_core.domain.execution_context import ExecutionContext

from tests.utils import assert_element_of_type
from yanga.cmake.cmake_backend import CMakeAddExecutable, CMakeCustomTarget, CMakeTargetLinkLibraries, LinkScope
from yanga.zephyr.cmake import ZephyrCMakeGenerator


def test_components_link_into_zephyr_app(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ZephyrCMakeGenerator(execution_context, output_dir).generate()

    assert not find_elements_of_type(elements, CMakeAddExecutable)
    app_link = assert_element_of_type(elements, CMakeTargetLinkLibraries, lambda element: element.target == "app")
    assert app_link.scope == LinkScope.PRIVATE
    assert set(app_link.libraries) == {"CompA_lib", "CompBNotTestable_lib"}
    component_links = [element for element in find_elements_of_type(elements, CMakeTargetLinkLibraries) if element.target != "app"]
    assert {element.target for element in component_links} == {"CompA_lib", "CompBNotTestable_lib"}
    assert {library for element in component_links for library in element.libraries} == {"zephyr_interface", "zephyr_generated_headers"}


def test_build_target_waits_for_the_zephyr_elf(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ZephyrCMakeGenerator(execution_context, output_dir).generate()

    build_target = assert_element_of_type(elements, CMakeCustomTarget, lambda element: element.name == "build")
    assert build_target.depends == ["${logical_target_for_zephyr_elf}"]
