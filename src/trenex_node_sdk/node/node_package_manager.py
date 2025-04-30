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
    def __init__(self, root_dir: str):
        path = Path(root_dir)

        if not path.is_absolute():
            raise ValueError(f"Root directory must be an absolute path: {root_dir}")
        if not path.exists():
            raise ValueError(f"Root directory does not exist: {root_dir}")
        if not path.is_dir():
            raise ValueError(f"Root directory is not a directory: {root_dir}")

        self.root_dir: Path = path
        # by default, defer nodes_dir initialization until accessed
        self._nodes_dir: Path = None

    @staticmethod
    def _validate_dir(path: Path, name: str):
        if not path.is_absolute():
            raise ValueError(f"{name} must be an absolute path: {path}")
        if not path.exists():
            raise ValueError(f"{name} does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"{name} is not a directory: {path}")

    @property
    def nodes_dir(self) -> Path:
        """
        Directory where node packages are stored.
        Defaults to '<root_dir>/nodes' if not set explicitly, creating it if necessary.
        """
        if self._nodes_dir is None:
            default = self.root_dir / "nodes"
            # create the default directory if it doesn't exist
            if not default.exists():
                default.mkdir(parents=True, exist_ok=True)
            # ensure it's a directory
            if not default.is_dir():
                raise FileNotFoundError(f"Default nodes_dir path exists and is not a directory: {default}")
            self._nodes_dir = default
        return self._nodes_dir

    @nodes_dir.setter
    def nodes_dir(self, dir_path: str):
        """
        Set a custom directory for node packages.
        """
        path = Path(dir_path)
        # validate custom path
        self._validate_dir(path, "nodes_dir")
        self._nodes_dir = path
        
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
