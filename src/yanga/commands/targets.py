"""Command line utility to create target documentation from targets data."""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from pathlib import Path

from clanguru.doc_generator import DocStructure, MarkdownFormatter, Section, TextContent
from py_app_dev.core.cmd_line import Command, register_arguments_for_config_dataclass
from py_app_dev.core.config import BaseConfigJSONMixin
from py_app_dev.core.logging import logger, time_it
from yanga_core.commands.base import create_config

from yanga.cmake.generator import GeneratedFile
from yanga.cmake.targets import Target, TargetsData, TargetType

DEPENDENCY_TREE_CSS = """
<style>
.dependency-tree {
    font-family: monospace;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 4px;
    padding: 10px;
    margin: 10px 0;
}
.dependency-tree details {
    margin-left: 10px;
}
.dependency-tree summary {
    cursor: pointer;
    padding: 2px 0;
}
.dependency-tree summary:hover {
    background-color: #e9ecef;
}
.dependency-tree ul {
    margin: 5px 0;
    padding-left: 20px;
}
.dependency-tree li {
    margin: 2px 0;
    list-style-type: none;
}
.dependency-tree strong {
    color: #0066cc;
}
.dependency-tree em {
    color: #666;
}
.dependency-tree code {
    background-color: #f1f3f4;
    color: #333;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}
.target-info {
    background: #f8f9fa;
    border-left: 4px solid #0066cc;
    padding: 10px;
    margin: 10px 0;
}
.target-info ul {
    margin: 5px 0;
    padding-left: 20px;
}
.target-info li {
    margin: 2px 0;
}
</style>"""


@dataclass
class TargetTreeNode:
    """Represents a node in the target dependency tree."""

    target: Target
    children: list["TargetTreeNode"] = field(default_factory=list)


class TargetDependencyTreeBuilder:
    """Builds and analyzes target dependency trees."""

    def __init__(self, targets_data: TargetsData) -> None:
        self.targets_data = targets_data
        self.targets_by_name = {target.name: target for target in targets_data.targets}
        # Create a mapping from output files to the targets that produce them
        self.outputs_to_targets = {}
        for target in targets_data.targets:
            for output in target.outputs:
                self.outputs_to_targets[str(output)] = target

    def generate_target_tree(self, target: Target | str) -> TargetTreeNode:
        """
        Generate a dependency tree for a given target.

        Design considerations:
        - Make sure to handle circular dependencies by keeping track of the nodes current dependency path.
        - Use caching to avoid redundant computations.
        - To determine dependencies map `depends` and `outputs` between targets.
        """
        if isinstance(target, str):
            input_target = self.targets_by_name.get(target) or self.outputs_to_targets.get(target)
            if not input_target:
                raise ValueError(f"Target '{target}' not found.")
        else:
            input_target = target

        def _build_tree(current_target: Target, path: set[str]) -> TargetTreeNode:
            if current_target.name in path:
                return TargetTreeNode(current_target)  # Circular dependency detected, stop here

            node = TargetTreeNode(current_target)
            # Add current target to the path for circular dependency detection
            new_path = path | {current_target.name}

            # Track unique target dependencies to avoid duplicates
            unique_dep_targets: dict[str, Target] = {}

            for dep_name in current_target.depends:
                dep_name_str = str(dep_name)
                dep_target = self.targets_by_name.get(dep_name_str) or self.outputs_to_targets.get(dep_name_str)
                if dep_target and dep_target.name not in unique_dep_targets:
                    unique_dep_targets[dep_target.name] = dep_target

            # Add child nodes for unique target dependencies
            for dep_target in unique_dep_targets.values():
                child_node = _build_tree(dep_target, new_path)
                node.children.append(child_node)

            return node

        return _build_tree(input_target, set())


class TargetDocumentationGenerator:
    """Generates documentation structure for targets using DocStructure."""

    def __init__(self, targets_data: TargetsData) -> None:
        self.targets_data = targets_data
        self.tree_builder = TargetDependencyTreeBuilder(targets_data)

    def create_doc_structure(self, targets_names: list[str]) -> DocStructure:
        """
        Create a DocStructure for target dependencies documentation.

        Optimizations:
        - Compute root targets once (was computed twice).
        - Pass pre-computed root targets to summary section.
        """
        doc = DocStructure("Build Targets")

        styles_section = Section("Styles")
        styles_section.add_content(TextContent(DEPENDENCY_TREE_CSS))
        doc.add_section(styles_section)

        targets = self._find_targets(targets_names)
        self._add_summary_section(doc, targets)
        if targets:
            self._add_root_targets_sections(doc, targets)
        else:
            no_targets_section = Section("Targets")
            no_targets_section.add_content(TextContent("No matching targets were found in the provided targets data."))
            doc.add_section(no_targets_section)
        return doc

    def _find_targets(self, targets_names: list[str]) -> list[Target]:
        """Find and return targets by their names."""
        targets = []
        for name in targets_names:
            target = self.tree_builder.targets_by_name.get(name) or self.tree_builder.outputs_to_targets.get(name)
            if target:
                targets.append(target)
        return targets

    def _add_summary_section(self, doc: DocStructure, targets: list[Target]) -> None:
        """Add summary statistics section using pre-computed root targets."""
        total_targets = len(self.targets_data.targets)
        summary_text = (
            f"- **Total targets**: {total_targets}\n"
            f"- **Root targets (CMakeCustomTargets only)**: {len(targets)}\n\n"
            "This document provides an overview of CMake custom target dependencies. Only CMakeCustomTargets are shown as root targets."
        )
        section = Section("Summary")
        section.add_content(TextContent(summary_text))
        doc.add_section(section)

    def _add_root_targets_sections(self, doc: DocStructure, targets: list[Target]) -> None:
        """Add sections for each root target with dependency trees."""
        root_targets_section = Section("Root Targets (CMakeCustomTargets)")
        root_targets_section.add_content(TextContent("These are the main CMakeCustomTargets that are not dependencies of other targets."))

        for target in targets:
            target_section = self._create_target_section(target)
            root_targets_section.add_subsection(target_section)

        doc.add_section(root_targets_section)

    def _create_target_section(self, target: Target) -> Section:
        """Create a section for a single target with its information and dependency tree."""
        target_section = Section(target.name)

        # Get the target tree structure
        target_node = self.tree_builder.generate_target_tree(target)

        # Add target information
        info_text = self._create_target_info(target)
        target_section.add_content(TextContent(info_text))

        # Add dependency tree
        tree_html = self._generate_dependency_tree(target_node)
        if tree_html:
            full_tree_html = f'**Dependencies:**\n\n<div class="dependency-tree">\n<ul>\n{tree_html}\n</ul>\n</div>'
            target_section.add_content(TextContent(full_tree_html))

        return target_section

    def _create_target_info(self, target: Target) -> str:
        """Create basic information about the target."""
        info_parts = []

        if target.description:
            info_parts.append(f"**Description:** {target.description}")

        info_parts.append(f"**Type:** {target.target_type.name}")

        if target.outputs:
            outputs_str = ", ".join(f"`{output}`" for output in target.outputs)
            info_parts.append(f"**Outputs:** {outputs_str}")

        return "\n\n".join(info_parts)

    def _generate_dependency_tree(self, target_node: TargetTreeNode, visited: set[str] | None = None) -> str:
        """
        Generate HTML tree for a target and its dependencies with collapsible structure.

        Creates an interactive HTML tree using details/summary elements for navigation.
        Uses structured lists to show name, outputs, and dependencies clearly.
        """
        if visited is None:
            visited = set()

        if target_node.target.name in visited:
            display_name = "custom command" if target_node.target.target_type == TargetType.CUSTOM_COMMAND else target_node.target.name
            return f"<li><strong>{display_name}</strong> <em>(circular dependency)</em></li>"

        visited = visited.copy()
        visited.add(target_node.target.name)

        # Build target information
        target = target_node.target
        display_name = "custom command" if target.target_type == TargetType.CUSTOM_COMMAND else target.name

        # Build the node structure
        node_info = self._create_node_info(target, target_node.children, visited)

        return node_info

    def _create_node_info(self, target: Target, children: list[TargetTreeNode], visited: set[str]) -> str:
        """Create structured information for a target node."""
        display_name = "custom command" if target.target_type == TargetType.CUSTOM_COMMAND else target.name

        # Build the main structure
        parts = ["<li>"]

        if children:
            # Collapsible structure for nodes with dependencies
            parts.append("<details>")
            parts.append(f"<summary><strong>{display_name}</strong></summary>")
            parts.append("<ul>")

            # Add target details
            if target.description:
                parts.append(f"<li><strong>Description:</strong> {target.description}</li>")

            # Add outputs if any
            if target.outputs:
                parts.append("<li><strong>Outputs:</strong><ul>")
                for output in target.outputs:
                    parts.append(f"<li><code>{output}</code></li>")
                parts.append("</ul></li>")

            # Add dependencies
            if target.depends:
                parts.append("<li><strong>Dependencies:</strong><ul>")

                # Group dependencies by type
                dependency_children = {}
                external_deps = []
                provided_deps = []

                # Get all outputs from child targets for comparison
                child_outputs = set()
                for child in children:
                    for output in child.target.outputs:
                        child_outputs.add(str(output))

                # Find which dependencies are represented as children vs external
                child_targets = {child.target.name: child for child in children}

                for dep_name in target.depends:
                    dep_name_str = str(dep_name)
                    if dep_name_str in child_targets:
                        dependency_children[dep_name_str] = child_targets[dep_name_str]
                    elif dep_name_str in child_outputs:
                        # It's provided by a child target's outputs, show without (external) tag
                        provided_deps.append(dep_name_str)
                    else:
                        # Mark as external if it's not provided by any child target's outputs
                        external_deps.append(dep_name_str)

                # Add external dependencies first (simple list items)
                for ext_dep in external_deps:
                    parts.append(f"<li><code>{ext_dep}</code> <em>(external)</em></li>")

                # Add provided dependencies (without external tag)
                for provided_dep in provided_deps:
                    parts.append(f"<li><code>{provided_dep}</code></li>")

                # Add child dependencies (collapsible)
                for child in children:
                    child_html = self._generate_dependency_tree(child, visited)
                    parts.append(child_html)

                parts.append("</ul></li>")

            parts.extend(["</ul>", "</details>"])
        else:
            # Structure for leaf nodes - use collapsible format for consistency
            parts.append("<details>")
            parts.append(f"<summary><strong>{display_name}</strong></summary>")
            parts.append("<ul>")

            # Add target details
            if target.description:
                parts.append(f"<li><strong>Description:</strong> {target.description}</li>")

            # Add outputs if any
            if target.outputs:
                parts.append("<li><strong>Outputs:</strong><ul>")
                for output in target.outputs:
                    parts.append(f"<li><code>{output}</code></li>")
                parts.append("</ul></li>")

            # Add dependencies if any
            if target.depends:
                parts.append("<li><strong>Dependencies:</strong><ul>")
                for dep_name in target.depends:
                    parts.append(f"<li><code>{dep_name}</code></li>")
                parts.append("</ul></li>")

            parts.extend(["</ul>", "</details>"])

        parts.append("</li>")
        return "".join(parts)


def create_doc_structure(targets_data: TargetsData, targets: list[str], title: str = "Build Targets") -> DocStructure:
    """Utility function to create a DocStructure for targets documentation."""
    generator = TargetDocumentationGenerator(targets_data)
    doc_structure = generator.create_doc_structure(targets)
    doc_structure.title = title
    return doc_structure


@dataclass
class CommandArgs(BaseConfigJSONMixin):
    variant_targets_data_file: Path = field(metadata={"help": "Variant targets data JSON file."})
    output_file: Path = field(metadata={"help": "Output targets data documentation file."})
    targets: list[str] = field(default_factory=list, metadata={"help": "Targets to include in the documentation. Can be used multiple times."})


class TargetsDocCommand(Command):
    def __init__(self) -> None:
        super().__init__("targets_doc", "Create a variant targets data documentation file with collapsible dependency trees.")
        self.logger = logger.bind()

    @time_it("targets_doc command")
    def run(self, args: Namespace) -> int:
        self.logger.info(f"Running {self.name} with args {args}")
        cmd_args = create_config(CommandArgs, args)
        targets_data = TargetsData.from_json_file(cmd_args.variant_targets_data_file)
        content = MarkdownFormatter().format(create_doc_structure(targets_data, cmd_args.targets))
        self.logger.debug(f"Generate documentation for targets: {cmd_args.targets}")
        GeneratedFile(cmd_args.output_file, content).to_file()
        self.logger.info(f"Generated target documentation at {cmd_args.output_file}")
        return 0

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, CommandArgs)
