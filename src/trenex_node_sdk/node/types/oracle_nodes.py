from abc import ABC, abstractmethod
from core.node.node_base import Node

class OracleNode(Node):
    """
    Base class for Oracle Nodes.
    Provides an interface for generating a trading signal.
    """

class StrategyNode(OracleNode):
    """
    Base class for strategy based Oracle Node.
    Extends OracleNode with methods for executing trades.
    """
    

class ModelNode(OracleNode):
    """
    Base class for models that generate signals based on learned or computed patterns.
    Models can be machine learning-based, statistical, or rule-based.
    """

    @abstractmethod
    def update():
        pass

    @abstractmethod
    def train(self):
        """
        Train the model using historical or simulated data.
        """
        pass

    @abstractmethod
    def predict(self):
        """
        Generate a prediction (signal) based on input data.
        """
        pass
