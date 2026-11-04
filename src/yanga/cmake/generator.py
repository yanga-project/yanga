from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.generated_file import GeneratedFile, GeneratedFileIf

from .cmake_backend import CMakeElement

__all__ = ["CMakeFile", "CMakeGenerator", "GeneratedFile", "GeneratedFileIf"]


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
