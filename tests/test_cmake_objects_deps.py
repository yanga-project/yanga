from pathlib import Path

import pytest
from yanga_core.domain.execution_context import ExecutionContext

from tests.utils import assert_element_of_type
from yanga.cmake.cmake_backend import CMakeCustomCommand, CMakeCustomTarget, CMakePath
from yanga.cmake.objects_deps import ObjectsDepsCMakeGenerator


@pytest.fixture
def objects_deps_generator(execution_context: ExecutionContext, output_dir: Path) -> ObjectsDepsCMakeGenerator:
    return ObjectsDepsCMakeGenerator(execution_context, output_dir)


def test_generate(objects_deps_generator: ObjectsDepsCMakeGenerator) -> None:
    elements = objects_deps_generator.generate()
    assert elements

    # Should generate one custom command and one custom target
    custom_command = assert_element_of_type(elements, CMakeCustomCommand)
    assert custom_command.description == "Run clanguru to generate the objects dependencies report"
    assert custom_command.depends == ["build"]
    output_path = assert_element_of_type(custom_command.outputs, CMakePath)
    assert "objects_deps.html" in output_path.to_string()

    custom_target = assert_element_of_type(elements, CMakeCustomTarget)
    assert custom_target.name == "objects_deps"
    assert custom_target.description == "Generate objects dependencies report"
    assert custom_target.depends == custom_command.outputs
