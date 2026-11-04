from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from py_app_dev.core.find import find_elements_of_type

T = TypeVar("T")


def _assert_elements(elements: list[Any] | None, element_type: type[T], expected_count: int, filter_fn: Callable[[T], bool] | None = None) -> list[T]:
    """Helper method to assert and return elements based on type and optional filter."""
    assert elements is not None, "Elements list is None"
    found_elements = find_elements_of_type(elements, element_type)

    if expected_count != 0:
        assert found_elements, f"No element of type {element_type.__name__} found"

    filtered_elements = found_elements
    if filter_fn:
        filtered_elements = [elem for elem in found_elements if filter_fn(elem)]

    assert len(filtered_elements) == expected_count, f"Expected {expected_count} elements of type {element_type.__name__} that met the criteria, but found {len(filtered_elements)}"

    return filtered_elements


def assert_element_of_type(elements: list[Any] | None, element_type: type[T], filter_fn: Callable[[T], bool] | None = None) -> T:
    """Assert that exactly one element of the given type exists, optionally needs to meet filter condition."""
    return _assert_elements(elements, element_type, 1, filter_fn)[0]


def assert_elements_of_type(elements: list[Any] | None, element_type: type[T], count: int, filter_fn: Callable[[T], bool] | None = None) -> list[T]:
    """Assert that exactly `count` elements of the given type exist, optionally needs to meet filter condition."""
    return _assert_elements(elements, element_type, count, filter_fn)


def write_file(file: Path, content: str) -> Path:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    return file


def this_repository_root_dir() -> Path:
    return Path(__file__).parent.parent.absolute()
