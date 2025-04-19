from enum import Enum
from typing import Dict, Tuple, Any, TYPE_CHECKING, List, Union
from dataclasses import dataclass

from trenex_node_sdk.memory import SharedMemoryPort

if TYPE_CHECKING:
    from trenex_node_sdk.node.node_base import Node

class IO:
    """
    Represents an individual Input/Output (IO) channel for a node.

    Attributes:
        name (str): The name of the IO channel.
        dtype (type): The data type for this IO.
        shape (tuple): The shape of the data for this IO.
        shm (SharedMemoryPort): The associated shared memory port (if initialized).
    """

    class IOType(Enum):
        INPUT = 1
        OUTPUT = 2

    def __init__(self, name: str, io_type: IOType, parent: "NodeIO", dtype: type = float, shape: Tuple[int, ...] = None) -> None:
        self.name: str = name
        self.dtype: type = dtype
        self.shape: Tuple[int, ...] = shape
        self.shm: SharedMemoryPort = None
        self.parent: NodeIO = parent
        self._io_type: IO.IOType = io_type
        # For input, store a single connection (or None). For output, use a list to hold connections.
        self._io_cntn: Union[None, IO, List[IO]] = None if self._io_type == IO.IOType.INPUT else []

    def connect(self, other: 'IO') -> None:
        """
        Connect this IO to another IO. Input ports may only be connected
        to one output port, while output ports can connect to multiple input ports.
        """
        if self._io_type == other._io_type:
            raise ValueError(f"Cannot connect two IOs of the same type: {self._io_type.name}")

        # Identify which is input and which is output
        if self._io_type == IO.IOType.INPUT:
            input_io = self
            output_io = other
        else:
            input_io = other
            output_io = self

        # Ensure the input IO is not already connected.
        if input_io._io_cntn is not None:
            raise ValueError("This input port is already connected to another output port.")

        # Establish the connection in both directions.
        input_io._io_cntn = output_io
        if input_io not in output_io._io_cntn:
            output_io._io_cntn.append(input_io)

    def disconnect(self, other: 'IO') -> None:
        """
        Disconnect this IO from another IO.
        """
        # If self is an input, then its connection must be 'other'
        if self._io_type == IO.IOType.INPUT:
            if self._io_cntn != other:
                raise ValueError("No such connection exists to disconnect.")
            # Remove the input from the output's connection list.
            if isinstance(other._io_cntn, list) and self in other._io_cntn:
                other._io_cntn.remove(self)
            self._io_cntn = None
        else:
            # self is an output (thus _io_cntn is a list)
            if not isinstance(self._io_cntn, list) or other not in self._io_cntn:
                raise ValueError("No such connection exists to disconnect.")
            self._io_cntn.remove(other)
            # Also remove the output from the input’s connection if it points back.
            if other._io_cntn == self:
                other._io_cntn = None

    def set_shm(self, shm: SharedMemoryPort) -> None:
        """
        Set the shared memory port for this IO.

        Args:
            shm (SharedMemoryPort): The shared memory port to associate with this IO.
        """
        self.shm = shm

    def get_shm(self) -> SharedMemoryPort:
        """
        Get the shared memory port associated with this IO.

        Returns:
            SharedMemoryPort: The associated shared memory port.
        """
        return self.shm

    def initialize_shm(self) -> None:
        """
        Initialize the shared memory port if it hasn't been initialized.
        """
        if self.shm is None:
            self.shm = SharedMemoryPort(name=self.name, dtype=self.dtype, shape=self.shape)

    def write(self, data: Any) -> None:
        """
        Write data to the associated shared memory port.

        Args:
            data: The data to write.
        """
        if self.shm:
            self.shm.write(data)
        else:
            raise RuntimeError(f"Shared memory for IO '{self.name}' is not initialized.")

    def read(self) -> Any:
        """
        Read data from the associated shared memory port.

        Returns:
            The data read from the shared memory port, or None if not set.
        """
        if self.shm:
            return self.shm.read()
        return None

    def __repr__(self) -> str:
        return f"IO(name={self.name}, shape={self.shape}, dtype={self.dtype.__name__})"


class NodeIO:
    """
    Manages multiple IO instances for a node.
    
    IO instances are stored internally and exposed via dot notation.
    
    Attributes:
        _node (Node): The parent node this IO belongs to.
        _io_type (IOType): Specifies whether these IOs are inputs or outputs.
        _ios (Dict[str, IO]): Dictionary mapping IO names to IO instances.
    """

    def __init__(self, parent_node: "Node", io_type: "IO.IOType") -> None:
        self._node = parent_node
        self._io_type = io_type
        # Internal dictionary to hold IO instances.
        self.__dict__["_ios"]: Dict[str, IO] = {}   # type: ignore

    def create_io(self, name: str, dtype: type = float, shape: Tuple[int, ...] = None) -> None:
        """
        Create an IO object with the given name and attach it as an attribute.

        Args:
            name (str): The name of the IO.
            dtype (type): The data type for the IO (default is float).
            shape (tuple): The expected shape of the IO data.

        Raises:
            ValueError: If an IO with the given name already exists.
        """
        if name in self._ios:
            raise ValueError(f"IO with name '{name}' already exists.")
        io = IO(name=name, io_type=self._io_type, parent=self, dtype=dtype, shape=shape)
        self._ios[name] = io
        super().__setattr__(name, io)

    def get(self, name: str) -> IO:
        """
        Retrieve an IO object by its name.

        Args:
            name (str): The name of the IO.

        Returns:
            IO: The IO object with the specified name.

        Raises:
            KeyError: If no IO with the given name exists.
        """
        if name in self._ios:
            return self._ios[name]
        raise KeyError(f"IO with name '{name}' not found.")

    @property
    def all(self) -> Dict[str, IO]:
        """
        Get all IO objects as a dictionary.

        Returns:
            Dict[str, IO]: A dictionary mapping IO names to IO objects.
        """
        return self._ios

    def __getattr__(self, name: str) -> IO:
        """
        Provide dot notation access to IO objects stored in _ios.

        Args:
            name (str): The name of the IO.

        Returns:
            IO: The IO object if it exists.

        Raises:
            AttributeError: If no IO with the given name exists.
        """
        if name in self._ios:
            return self._ios[name]
        raise AttributeError(f"No IO named '{name}' found.")

    def __repr__(self) -> str:
        return f"{self._io_type.name.capitalize()}IO({list(self._ios.keys())})"

@dataclass
class IOConnection:
    out_IO: "IO"
    in_IO: "IO"