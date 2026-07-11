"""metacsp: Python port of the Meta-CSP Framework (org.metacsp).

Original Java framework by Federico Pecora,
https://github.com/FedericoPecora/meta-csp-framework (MIT).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("metacsp")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"
