from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from yanga_core.domain.components import Component
from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.generated_file import GeneratedFile, GeneratedFileIf

from .cmake_backend import CMakeElement

__all__ = ["CMakeFile", "CMakeGenerator", "GeneratedFile", "GeneratedFileIf", "report_level", "subcomponent_names"]


def subcomponent_names(component: Component) -> list[str]:
    """Down to the components that are not containers, like the container test target."""
    return [name for subcomponent in component.subcomponents for name in [subcomponent.name, *subcomponent_names(subcomponent)]]


def report_level(component: Component) -> str:
    """The report level tag of a component's entries: an integration component tests a group of components, like a container."""
    return "container" if component.is_container or component.integrates else "component"


class CMakeGenerator(ABC):
    """Base class for CMake generators."""

    def __init__(self, execution_context: ExecutionContext, output_dir: Path, config: dict[str, Any] | None = None) -> None:
        self.execution_context = execution_context
        self.config = config
        self.output_dir = output_dir

    @abstractmethod
    def generate(self) -> list[CMakeElement]:
        pass


class CMakeFile(GeneratedFileIf):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.content: list[CMakeElement] = []

    def to_string(self) -> str:
        return "\n".join(str(elem) for elem in self.content)

    def append(self, content: CMakeElement | None) -> "CMakeFile":
        if content:
            self.content.append(content)
        return self

    def extend(self, content: list[CMakeElement]) -> "CMakeFile":
        for element in content:
            self.append(element)
        return self
