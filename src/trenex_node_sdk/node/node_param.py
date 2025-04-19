from typing import Dict, Tuple, Any, List, TYPE_CHECKING


if TYPE_CHECKING:
    from trenex_node_sdk.node.node_base import Node

# ---------------------------
# Param and Parameters Classes
# ---------------------------

class Param:
    """
    Represents an individual parameter.

    Attributes:
      name: Name of the parameter.
      dtype: Data type of the parameter.
      allowed_range: Optional tuple (min, max) for a continuous range.
      allowed_values: Optional list of allowed values.
      value: The current value of the parameter.
      description: Description of the parameter.
    """
    def __init__(self, name: str, dtype: type, default_value: Any = None,
                 allowed_range: Tuple[Any, Any] = None, allowed_values: List[Any] = None,
                 description: str = "") -> None:
        # Set attributes bypassing our overridden __setattr__
        super().__setattr__("name", name)
        super().__setattr__("dtype", dtype)
        super().__setattr__("allowed_range", allowed_range)
        super().__setattr__("allowed_values", allowed_values)
        super().__setattr__("description", description)
        # Use our __setattr__ to set the value (which validates)
        self.value = default_value

    def set_allowed_range(self, new_range: Tuple[Any, Any]) -> None:
        """Update the allowed range for this parameter."""
        self.allowed_range = new_range

    def set_allowed_values(self, new_values: List[Any]) -> None:
        """Update the allowed values for this parameter."""
        self.allowed_values = new_values

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "value":
            if not isinstance(value, self.dtype):
                raise ValueError(f"Value for '{self.name}' must be of type {self.dtype}, got {type(value).__name__}.")
            if self.allowed_range is not None:
                min_val, max_val = self.allowed_range
                if not (min_val <= value <= max_val):
                    raise ValueError(f"Value for '{self.name}' must be between {min_val} and {max_val}.")
            if self.allowed_values is not None:
                if value not in self.allowed_values:
                    raise ValueError(f"Value for '{self.name}' must be one of {self.allowed_values}.")
        super().__setattr__(key, value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value == other.value
        return self.value == other

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value < other.value
        return self.value < other

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value <= other.value
        return self.value <= other

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value > other.value
        return self.value > other

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value >= other.value
        return self.value >= other

    def __repr__(self) -> str:
        return f"Param(name={self.name}, value={self.value}, dtype={self.dtype.__name__})"

class Parameters:
    """
    Holds individual parameters as attributes.
    
    Use add_param() to add a parameter. Once added, the parameter can be accessed and updated directly.
    
    Example:
        params = Parameters()
        params.add_param(Param("limit", int, default_value=100))
        print(params.limit)   # prints 100
        params.limit = 150    # updates the value to 150
        params.new_param = 42 # automatically creates a new Param for 'new_param' with type int and value 42.
    """
    def __init__(self, parent_node: "Node") -> None:
        self.__dict__["_node"] = parent_node
        # Internal dictionary to track Param objects.
        self.__dict__["_params"] = {}

    def add_param(self, param: Param) -> None:
        self._params[param.name] = param
        super().__setattr__(param.name, param)

    def get(self, name: str) -> Any:
        if name in self._params:
            return self._params[name].value
        raise KeyError(f"Parameter '{name}' not found.")

    def update(self, name: str, value: Any) -> None:
        if name in self._params:
            setattr(self, name, value)
        else:
            raise ValueError(f"Parameter '{name}' is not of type Param.")

    @property
    def all_params(self) -> Dict[str, Param]:
        return self._params
    
    @property
    def parent(self) -> "Node":
        parent = self.__dict__.get("_node", None)
        return parent

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_node", "_params"}:
            raise AttributeError("Cannot define parameter named _node or _params")

        if isinstance(value, Param):
            self._params[name] = value
            super().__setattr__(name, value)
        else:
            if name in self.__dict__.get("_params", {}) and isinstance(self._params[name], Param):
                self._params[name].value = value
            else:
                new_param = Param(name=name, dtype=type(value), default_value=value)
                self._params[name] = new_param
                super().__setattr__(name, new_param)

    def __getattr__(self, name: str) -> Any:
        if name in self.__dict__.get("_params", {}):
            return self.__dict__["_params"][name].value
        raise AttributeError(f"Parameter '{name}' not found.")

    def __repr__(self) -> str:
        return f"Parameters({self._params})"
