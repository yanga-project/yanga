from pathlib import Path

from py_app_dev.core.logging import logger


class CMakeRunner:
    executable = "cmake"

    def __init__(self, project_dir: Path, build_dir: Path) -> None:
        self.logger = logger.bind()
        self.project_dir = project_dir
        self.build_dir = build_dir

    def get_configure_command(self, toolchain_file: str | None, variant_name: str | None, platform_name: str | None, build_type: str | None = None) -> list[str | Path]:
        cmake_args = [
            "-S",
            self.project_dir.absolute().as_posix(),
            "-B",
            self.build_dir.absolute().as_posix(),
            "-G",
            "Ninja",
        ]
        if toolchain_file:
            cmake_args.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}")
        if variant_name:
            cmake_args.append(f"-DVARIANT={variant_name}")
        if platform_name:
            cmake_args.append(f"-DPLATFORM={platform_name}")
        if build_type:
            cmake_args.append(f"-DCMAKE_BUILD_TYPE={build_type}")
        return [self.executable, *cmake_args]

    def get_build_command(self, target: str = "all") -> list[str | Path]:
        return [
            self.executable,
            "--build",
            self.build_dir.absolute().as_posix(),
            "--target",
            target,
            "--",
        ]
