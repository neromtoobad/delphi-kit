"""delphi-kit: read and trade Delphi prediction markets from Python, with no API key."""

from .client import Delphi, DelphiError, InsufficientFunds
from .models import Market, Position, Quote, Trade
from .networks import NETWORKS, Deployment, Network

__all__ = ["Delphi", "DelphiError", "InsufficientFunds", "Market", "Position", "Quote", "Trade",
           "NETWORKS", "Network", "Deployment"]
__version__ = "0.1.0"
