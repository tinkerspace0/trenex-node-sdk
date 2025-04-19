# core/plugin/exchange_interface.py
from abc import abstractmethod
from core.node.node_base import Node
from core.debug.profiler import Profiler

profile = Profiler.profile

class ExchangeInterface(Node):
    """
    Abstract interface for fetching essential market data from an exchange.
    """
    @profile
    @abstractmethod
    def fetch_ticker(self, symbol: str) :
        pass

    @profile
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        pass

    @profile
    @abstractmethod
    def fetch_recent_trades(self, symbol: str, limit: int = 20):
        pass

    @profile
    @abstractmethod
    def fetch_order_book(self, symbol: str, depth: int = 10):
        pass

    @profile
    @abstractmethod
    def fetch_market_status(self):
        pass

    @profile
    @abstractmethod
    def fetch_24h_volume(self, symbol: str):
        pass
