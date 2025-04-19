import shutil
from pathlib import Path

class NodePackageManager:
    """
    Provides utilities for scaffolding and managing standalone single-node packages.

    Expects a directory of templates at:
        <trenex_node_sdk>/templates/node_package/
    containing placeholder files:
      - NodeTemplate.py
      - node.yaml
      - pyproject.toml

    The placeholders 'NodeTemplate' and 'category' in filenames and file contents
    will be replaced with the actual node name and category.
    """

    @staticmethod
    def create_node_template(destination: str, node_name: str, category: str = "custom") -> None:
        """
        Scaffold a new node package.

        Args:
            destination (str): Path to the folder where the new package should be created.
            node_name (str): The name of the node class (and module) to create.
            category (str): The node category (default: 'custom').

        The function will:
          1. Copy the template directory into '<destination>/<node_name>'.
          2. Rename files and directories replacing 'NodeTemplate' with the given node_name.
          3. In each copied file, replace occurrences of 'NodeTemplate' with node_name,
             and 'category' with the provided category.
        """
        sdk_root = Path(__file__).parent.parent
        template_dir = sdk_root / "templates" / "node_package"
        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        dest_base = Path(destination) / node_name
        if dest_base.exists():
            raise FileExistsError(f"Destination already exists: {dest_base}")

        # Copy the entire template tree
        shutil.copytree(template_dir, dest_base)

        # Walk through copied files and rename/patch
        for path in list(dest_base.rglob('*')):
            # Rename files containing the placeholder
            if 'NodeTemplate' in path.name or 'category' in path.name:
                new_name = path.name.replace('NodeTemplate', node_name).replace('category', category)
                path = path.rename(path.with_name(new_name))

            # If it's a file, replace placeholders in its contents
            if path.is_file():
                text = path.read_text()
                text = text.replace('NodeTemplate', node_name)
                text = text.replace('category', category)
                path.write_text(text)
