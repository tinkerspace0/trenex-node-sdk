import io
import zipfile
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional
from cryptography.fernet import Fernet, InvalidToken

class NodePackageManager:
    """
    Manages encrypted node packages.

    - You can supply one or more Fernet keys when constructing the manager,
      or register them later via add_key().
    - pack_node_package() uses:
        • the provided key (if given), adding it to the set of keys, or
        • the first registered key otherwise.
    - import_node_package() will:
        • decrypt & unpack .npkg archives, or
        • validate & copy unpackaged node folders.
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
