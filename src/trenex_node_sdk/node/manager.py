# core/node/node_manager.py

import os
import importlib
import inspect
from typing import Dict, List, Tuple
from uuid import UUID

from trenex_node_sdk.node import Node
from trenex_node_sdk.utils.file import get_subdirectories

class NodeManager:
    # Cached dictionary mapping node categories to a list of available node class names.
    _nodes_cache: Dict[str, List[str]] = {}

    @classmethod
    def update_available_nodes(cls) -> Dict[str, List[str]]:
        """
        Scans the core/node/nodes folder and updates the internal cache with a dictionary
        mapping each node category to a list of available node class names.
        This method should be called when you want to refresh the list of available nodes.
        """
        # TODO: Ignore not node related files and python environment files like __pychache__
        result = {}
        base_dir = os.path.join(os.path.dirname(__file__), "nodes")
        if not os.path.exists(base_dir):
            raise FileNotFoundError(f"Nodes directory not found: {base_dir}")
        
        # Iterate over each category folder (e.g. "exchanges", "agents", etc.)
        for category in os.listdir(base_dir):
            category_dir = os.path.join(base_dir, category)
            if os.path.isdir(category_dir):
                result[category] = []
                # For each subdirectory in this category, scan for .py files
                for subdir in get_subdirectories(category_dir):
                    subdir_path = os.path.join(category_dir, subdir)
                    for fname in os.listdir(subdir_path):
                        if fname.endswith(".py") and fname != "__init__.py":
                            module_name = os.path.splitext(fname)[0]
                            # Build full module path: core.node.nodes.<category>.<subdir>.<module_name>
                            full_module_path = f"core.node.nodes.{category}.{subdir}.{module_name}"
                            try:
                                module = importlib.import_module(full_module_path)
                            except ImportError as e:
                                print(f"Error importing module {full_module_path}: {e}")
                                continue
                            # Inspect for classes defined in this module
                            for name, cls in inspect.getmembers(module, predicate=inspect.isclass):
                                # Only include classes defined in this module that are subclasses of Node (but not Node itself)
                                # and where the module filename equals the class name.
                                if (
                                    cls.__module__ == full_module_path and 
                                    issubclass(cls, Node) and 
                                    cls is not Node and 
                                    module_name == name
                                ):
                                    result[category].append(name)
                # Remove duplicates if any.
                result[category] = list(set(result[category]))
        cls._nodes_cache = result
        return result

    @classmethod
    def available_nodes(cls) -> Dict[str, List[str]]:
        """
        Returns the cached list of available nodes. If the cache is empty,
        it will automatically update it by scanning the folder.
        """
        if not cls._nodes_cache:
            return cls.update_available_nodes()
        return cls._nodes_cache

    @classmethod
    def create_node_instance(cls, category: str, node_class_name: str, **kwargs) -> Node:
        """
        Create an instance of a Node given the node category and node class name.
        It searches in the subdirectories of core/node/nodes/<category> for a module named exactly
        as the node class name (e.g., if node_class_name is "Binance", it will look for "Binance.py").
        """
        import inspect  # Ensure we import inspect for isabstract check

        base_dir = os.path.join(os.path.dirname(__file__), "nodes", category)
        if not os.path.exists(base_dir):
            raise FileNotFoundError(f"Category directory not found: {base_dir}")

        # Look into each subdirectory under the category
        for sub in os.listdir(base_dir):
            sub_path = os.path.join(base_dir, sub)
            if os.path.isdir(sub_path):
                candidate = os.path.join(sub_path, f"{node_class_name}.py")
                if os.path.exists(candidate):
                    # Build full module path: core.node.nodes.<category>.<sub>.<node_class_name>
                    full_module_path = f"core.node.nodes.{category}.{sub}.{node_class_name}"
                    try:
                        module = importlib.import_module(full_module_path)
                    except ImportError as e:
                        print(f"Error importing module {full_module_path}: {e}")
                        raise ImportError(f"Could not import module '{full_module_path}'.") from e
                    try:
                        node_class = getattr(module, node_class_name)
                    except AttributeError as e:
                        raise AttributeError(f"Module '{full_module_path}' does not have a class named '{node_class_name}'.") from e
                    
                    # Check if the node_class is abstract
                    if inspect.isabstract(node_class):
                        raise TypeError(f"Cannot instantiate abstract node class '{node_class_name}'.")
                    
                    return node_class(**kwargs)

        raise ImportError(f"Could not find node implementation for class '{node_class_name}' in category '{category}'.")
