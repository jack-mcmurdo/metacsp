"""Port of utility/logging/MetaCSPLogging.java (and LoggerNotDefined.java).

Wraps the stdlib :mod:`logging` module (D7). Every metacsp class logs to
``logging.getLogger("metacsp.<ClassName>")``, all children of the ``"metacsp"``
logger, so applications can configure them collectively or individually.

Java's ``LogBrowser``/``LinePainter`` (Swing log viewer) are not ported.
"""

from __future__ import annotations

import logging

__all__ = ["LoggerNotDefined", "get_logger", "set_level", "set_level_for"]

_ROOT_NAME = "metacsp"

# Library convention: attach a NullHandler so importing metacsp never
# configures or pollutes the application's logging setup.
logging.getLogger(_ROOT_NAME).addHandler(logging.NullHandler())


class LoggerNotDefined(Exception):
    """Port of utility/logging/LoggerNotDefined.java."""

    def __init__(self, cls: type):
        super().__init__(f"Class {cls.__name__} does not have a logger.")


def get_logger(cls: type) -> logging.Logger:
    """Return the logger for a metacsp class (Java ``MetaCSPLogging.getLogger``).

    :param cls: the class within which the logger will be used.
    """
    return logging.getLogger(f"{_ROOT_NAME}.{cls.__name__}")


def set_level(level: int | str) -> None:
    """Set the log level for all metacsp loggers (Java ``setLevel(Level l)``)."""
    logging.getLogger(_ROOT_NAME).setLevel(level)


def set_level_for(cls: type, level: int | str) -> None:
    """Set the log level for one class's logger (Java ``setLevel(Class c, Level l)``)."""
    get_logger(cls).setLevel(level)
