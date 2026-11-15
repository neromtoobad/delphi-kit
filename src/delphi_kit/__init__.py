"""delphi-kit is now Agon for Python: ``pip install agon-delphi`` and ``from agon import Delphi``.

This package only installs agon-delphi and re-exports it so old imports keep working.
Home: https://github.com/neromtoobad/agon/tree/main/python
"""

import warnings

from agon import *  # noqa: F401,F403
from agon import __all__  # noqa: F401

warnings.warn("delphi-kit is now agon-delphi: use `from agon import Delphi`. "
              "See https://github.com/neromtoobad/agon/tree/main/python", DeprecationWarning, stacklevel=2)

__version__ = "0.3.0"
