from yanga.cmake.cmake_backend import CMakeElement, CMakeTargetLinkLibraries, LinkLibrary, LinkScope
from yanga.cmake.create_executable import CreateExecutableCMakeGenerator


class ZephyrCMakeGenerator(CreateExecutableCMakeGenerator):
    """
    Zephyr owns the executable: the component libraries are linked into its `app` library.

    Each library links `zephyr_interface`, the target Zephyr keeps every compiler setting on;
    CMake usage requirements flow from library to consumer only, so `app` linking it is not
    enough. Not `zephyr_library_named()`: that registers only while Zephyr's own tree is
    processed, and from here it warns and drops the library. The object libraries linked into
    the static `app` are archived into it, which Zephyr then links whole.
    """

    # zephyr_generated_headers is Zephyr's ordering handle for its build-time generated headers
    # (kernel.h pulls zephyr/heap_constants.h); Zephyr wires it for its own libraries only.
    component_link_libraries = (LinkLibrary("zephyr_interface"), LinkLibrary("zephyr_generated_headers"))

    @property
    def executable_target_name(self) -> str:
        # Zephyr's final ELF target: building it builds `app` and every Zephyr library linked into the firmware.
        return "${logical_target_for_zephyr_elf}"

    def create_executable_elements(self, component_library_targets: list[str]) -> list[CMakeElement]:
        # Keyword form: Zephyr already used it on `app`, and CMake forbids mixing the two signatures.
        return [CMakeTargetLinkLibraries("app", component_library_targets, scope=LinkScope.PRIVATE)]
