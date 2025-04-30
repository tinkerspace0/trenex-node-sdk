import io
import zipfile
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Any
from cryptography.fernet import Fernet, InvalidToken
import importlib.util
import sys

class NodePackageManager:
    """
    Manages encrypted and unpackaged node packages.

    - You can supply one or more Fernet keys when constructing the manager,
      or register them later via add_key().
    - pack_node_package() uses:
        • the provided key (if given), adding it to the set of keys, or
        • the first registered key otherwise.
    - import_node_package() will:
        • decrypt & unpack .npkg archives, or
        • validate & copy unpackaged node folders.
    - list_nodes() lists all installed node packages.
    - create_node_instance() imports and returns an instance of a node class.
    - Default nodes_dir is '<root_dir>/nodes', auto-created on first access.
    """

    def __init__(
        self,
        root_dir: str,
        keys: Optional[List[str]] = None,
    ):
        # Validate and store root_dir
        path = Path(root_dir)
        self._validate_dir(path, "Root directory")
        self.root_dir: Path = path

        # nodes_dir will be lazy-created
        self._nodes_dir: Optional[Path] = None

        # Key management
        self._keys: List[str] = []
        self._fernets: List[Fernet] = []
        if keys:
            for k in keys:
                self.add_key(k)

    @staticmethod
    def _validate_dir(path: Path, name: str):
        if not path.is_absolute():
            raise ValueError(f"{name} must be an absolute path: {path}")
        if not path.exists():
            raise FileNotFoundError(f"{name} does not exist: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"{name} is not a directory: {path}")

    @staticmethod
    def _validate_node_folder(path: Path):
        """
        Ensure `path` is the root of a node package:
          - directory exists
          - contains node.yaml
          - contains pyproject.toml
        """
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        if not (path / "node.yaml").is_file():
            raise FileNotFoundError(f"Missing metadata file node.yaml in: {path}")
        if not (path / "pyproject.toml").is_file():
            raise FileNotFoundError(f"Missing metadata file pyproject.toml in: {path}")

    @property
    def nodes_dir(self) -> Path:
        """
        Directory where node packages are stored.
        Defaults to '<root_dir>/nodes', creating it if necessary.
        """
        if self._nodes_dir is None:
            default = self.root_dir / "nodes"
            default.mkdir(parents=True, exist_ok=True)
            if not default.is_dir():
                raise NotADirectoryError(
                    f"Default nodes_dir path exists and is not a directory: {default}"
                )
            self._nodes_dir = default
        return self._nodes_dir

    @nodes_dir.setter
    def nodes_dir(self, dir_path: str):
        """
        Set a custom directory for node packages.
        """
        path = Path(dir_path)
        self._validate_dir(path, "nodes_dir")
        self._nodes_dir = path

    @staticmethod
    def create_node_template(destination: str, node_name: str, category: str = "custom") -> None:
        """
        Scaffold a new node package.

        Args:
            destination: folder where the new package should be created.
            node_name: the name of the node class (and module).
            category: the node category (default: 'custom').

        Copies from '<sdk_root>/templates/node_package', renaming all
        'NodeTemplate' and 'category' placeholders.
        """
        sdk_root = Path(__file__).parent.parent
        template_dir = sdk_root / "templates" / "node_package"
        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        dest_base = Path(destination) / node_name
        if dest_base.exists():
            raise FileExistsError(f"Destination already exists: {dest_base}")

        shutil.copytree(template_dir, dest_base)
        for path in list(dest_base.rglob("*")):
            # rename files/dirs
            if "NodeTemplate" in path.name or "category" in path.name:
                new_name = path.name.replace("NodeTemplate", node_name).replace("category", category)
                path = path.rename(path.with_name(new_name))
            # replace contents
            if path.is_file():
                text = path.read_text()
                text = text.replace("NodeTemplate", node_name)
                text = text.replace("category", category)
                path.write_text(text)

    def add_key(self, key: str) -> None:
        """
        Register another Fernet key (for decryption or future encryption).

        Key must be a 44-character URL-safe base64-encoded string.
        """
        if not isinstance(key, str) or len(key) != 44:
            raise ValueError("Fernet key must be a 44-character URL-safe base64 string")
        f = Fernet(key.encode())  # will raise if invalid
        self._keys.append(key)
        self._fernets.append(f)

    def pack_node_package(
        self,
        src_dir: str,
        output_file: str,
        key: Optional[str] = None
    ) -> None:
        """
        Zip & encrypt a node folder into a single .npkg file.

        Args:
            src_dir: path to the node package directory (must contain node.yaml).
            output_file: path where to write the .npkg.
            key: optional Fernet key to use for this packaging; if provided,
                 adds it to the manager's key list and uses it. Otherwise uses the first registered key.
        """
        # Choose or register the key
        if key is not None:
            self.add_key(key)
            fernet = self._fernets[-1]
        else:
            if not self._fernets:
                raise RuntimeError("No encryption key available; register one via add_key().")
            fernet = self._fernets[0]

        src = Path(src_dir)
        # Validate it’s really a node folder
        self._validate_node_folder(src)

        # Zip in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in src.rglob("*"):
                zipf.write(f, arcname=f.relative_to(src))
        buf.seek(0)

        # Encrypt and write out
        token = fernet.encrypt(buf.read())
        Path(output_file).write_bytes(token)

    def import_node_package(self, src: str) -> Path:
        """
        Decrypt & unpack a .npkg (or validate & copy a node folder) into nodes_dir.
        Tries each registered key until one succeeds.
        Returns the Path to the installed package.
        """
        src_path = Path(src)

        # 1) Encrypted archive
        if src_path.suffix == ".npkg":
            encrypted = src_path.read_bytes()
            for f in self._fernets:
                try:
                    data = f.decrypt(encrypted)
                    break
                except InvalidToken:
                    continue
            else:
                raise ValueError("Failed to decrypt node package with any provided key.")

            pkg_name = src_path.stem
            dest = self.nodes_dir / pkg_name
            if dest.exists():
                raise FileExistsError(f"Node already exists: {dest}")

            with TemporaryDirectory(dir=self.root_dir) as tmpdir:
                buf = io.BytesIO(data)
                with zipfile.ZipFile(buf, "r") as zipf:
                    zipf.extractall(tmpdir)
                # Validate unpacked folder before final move
                tmp_pkg = Path(tmpdir)
                self._validate_node_folder(tmp_pkg)
                shutil.move(tmpdir, str(dest))

            return dest

        # 2) Plain folder
        elif src_path.is_dir():
            # Validate it’s truly the package root
            self._validate_node_folder(src_path)

            pkg_name = src_path.name
            dest = self.nodes_dir / pkg_name
            if dest.exists():
                raise FileExistsError(f"Node already exists: {dest}")
            shutil.copytree(src_path, dest)
            return dest

        else:
            raise ValueError(f"Unsupported package format: {src}")

    def list_nodes(self) -> List[str]:
        """
        Return a list of installed node package names in nodes_dir.
        Only directories containing valid node.yaml and pyproject.toml are included.
        """
        names: List[str] = []
        for entry in self.nodes_dir.iterdir():
            if entry.is_dir():
                try:
                    self._validate_node_folder(entry)
                    names.append(entry.name)
                except (FileNotFoundError, NotADirectoryError):
                    continue
        return names

    def create_node_instance(self, package_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Dynamically import and instantiate the node class from an installed package.

        Args:
            package_name: name of the node package (directory name under nodes_dir).
            *args, **kwargs: constructor arguments for the node class.

        Returns:
            An instance of the node class (class name == package_name).
        """
        pkg_dir = self.nodes_dir / package_name
        if not pkg_dir.is_dir():
            raise FileNotFoundError(f"Node package not found: {pkg_dir}")
        # Validate package folder
        self._validate_node_folder(pkg_dir)

        # Ensure __init__.py exists
        init_py = pkg_dir / "__init__.py"
        if not init_py.is_file():
            raise FileNotFoundError(f"Missing __init__.py in node package: {pkg_dir}")

        # Create a module spec for a package
        spec = importlib.util.spec_from_file_location(
            package_name,
            str(init_py),
            submodule_search_locations=[str(pkg_dir)]
        )
        module = importlib.util.module_from_spec(spec)
        # Insert into sys.modules so that `from .helper import ...` works
        sys.modules[package_name] = module
        spec.loader.exec_module(module)  # type: ignore

        # Instantiate the class (must be named exactly package_name)
        if not hasattr(module, package_name):
            raise AttributeError(f"Package '{package_name}' has no class '{package_name}'")
        cls = getattr(module, package_name)
        return cls(*args, **kwargs)

    def import_node_library(self, nlib_file: str) -> List[Path]:
        """
        Import a '.nlib' (zip of .npkg files) by unpacking and importing
        each contained node package. Returns list of installed package Paths.
        """
        lib_path = Path(nlib_file)
        if not lib_path.is_file() or lib_path.suffix != ".nlib":
            raise ValueError(f"Not a .nlib file: {nlib_file}")

        installed: List[Path] = []
        # Extract all .npkg files into a temp dir, then import each
        with TemporaryDirectory(dir=self.root_dir) as tmpdir:
            with zipfile.ZipFile(lib_path, "r") as zipf:
                zipf.extractall(tmpdir)

            for npkg_path in Path(tmpdir).glob("*.npkg"):
                installed_path = self.import_node_package(str(npkg_path))
                installed.append(installed_path)

        return installed

    def export_node_library(self, npkg_files: List[str], output_file: str) -> None:
        """
        Bundle a collection of .npkg files into a single '.nlib' archive.

        Args:
            npkg_files: list of file paths to existing .npkg packages.
            output_file: destination path for the .nlib (must end in .nlib).
        """
        out = Path(output_file)
        if out.suffix != ".nlib":
            raise ValueError(f"Output file must have '.nlib' extension: {output_file}")

        # Write a zip containing each .npkg at top level
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in npkg_files:
                p = Path(f)
                if not p.is_file() or p.suffix != ".npkg":
                    raise ValueError(f"Not a valid .npkg file: {f}")
                zipf.write(p, arcname=p.name)