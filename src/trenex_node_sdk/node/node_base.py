# core/node/node_base.py
from abc import ABC, abstractmethod
from typing import Dict, Tuple
import numpy as np
from dataclasses import dataclass

from trenex_node_sdk.node.node_io import NodeIO, IO
from trenex_node_sdk.node.node_param import Parameters
from trenex_node_sdk.memory.shared_memory_port import SharedMemoryPort

class Node(ABC):
    """
    Base class for all nodes (ie Components).
    Each node has a configuration (NodeConfig) that defines its inputs, outputs, and parameters.
    """
    def __init__(self, name: str = None):
        self.name = name if name else f"Node_{self.id}"
        self._static_params = Parameters(self)  # Static Parameters for the node.
        self._dynamic_params = Parameters(self) # Dynamic Parameters for the node.
        self._io_in = NodeIO(self, IO.IOType.INPUT)     # Input/Output interface for the node inputs.
        self._io_out = NodeIO(self, IO.IOType.OUTPUT)   # Input/Output interface for the node outputs.

    def get_static_params(self) :
        """
        Get the static/(runtime immutable) parameters of the node.
        """
        return self._static_params
    
    def get_dynamic_params(self) :
        """
        Get the dynamic/(runtime mutable) parameters of the node.
        """
        return self._dynamic_params
    
    def get_in_io(self) -> NodeIO:
        """
        Get the input/output interface for the node inputs.
        """
        return self._io_in
    
    def get_out_io(self) -> NodeIO:
        """
        Get the input/output interface for the node outputs.
        """
        return self._io_out
    
    def get_io(self) -> Tuple[NodeIO, NodeIO]:
        """
        Get the input/output interfaces for the node inputs and outputs.
        """
        return self._io_in, self._io_out
    
    def get_config(self) -> 'NodeConfig':
        """
        Get the configuration of the node.
        This includes static and dynamic parameters, and input/output
        definitions.
        """
        return NodeConfig(self, self._static_params, self._dynamic_params, self._io_in, self._io_out)
    
    def verify(self) -> None:
        """
        Verify the node configuration.
        This includes checking the static and dynamic parameters, and the input/output definitions.
        """
        # TODO - Check static and dynamic parameters for validity.
        # TODO - Check the input and output NodeIO for validity.
        pass

    @abstractmethod    
    def update_io(self) -> None:
        """
        Update the input and output definitions based on the current static parameters.
        Must be implemented in derived NodeConfig classes.
        """
        raise NotImplementedError("update_io() must be implemented in derived NodeConfig classes.")


    @abstractmethod
    def process(self) -> None:
        """Execute the node's processing logic."""
        raise NotImplementedError("Process method not implemented.")
    

@dataclass
class NodeConfig:
    def __init__(self, node: Node, static_params: Parameters, dynamic_params: Parameters, input_ios: NodeIO, output_ios: NodeIO):
        self.node: Node = node
        self.static_params: Parameters = static_params
        self.dynamic_params: Parameters = dynamic_params
        self.input_ios: NodeIO = input_ios
        self.output_ios: NodeIO = output_ios
