# core/plugin/data_plugin.py
from abc import abstractmethod
from typing import Dict, List
from core.node.node_base import Node
from core.debug.profiler import Profiler

profile = Profiler.profile


class DataNode(Node):
    """
    Abstract Data Processing Node for extracting meaningful informations out of raw market data.
    """

class IndicatorNode(DataNode):
    """
    Abstract Indicator Node for generating technical indicators from raw market data.
    """

class FeatureNode(DataNode):
    """
    Abstract Feature Node for generating features from raw market data.
    """
