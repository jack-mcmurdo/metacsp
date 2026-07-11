"""Port of framework/Domain.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from metacsp.exceptions import IllegalValueChoiceFunction
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.value_choice_function import ValueChoiceFunction
    from metacsp.framework.variable import Variable

__all__ = ["Domain"]


class Domain(ABC):
    """Represents the domain of a Variable, with ValueChoiceFunction support.

    ``value_choice_functions`` is a class attribute shared by all Domain
    subclasses (Java ``static HashMap``), keyed by the concrete Domain subclass.
    """

    value_choice_functions: ClassVar[dict[type, dict[str, ValueChoiceFunction] | None]] = {}

    def __init__(self, variable: Variable) -> None:
        self._variable = variable
        self.default_value_choice_function: str | None = None
        self.logger = get_logger(type(self))

    @property
    def variable(self) -> Variable:
        """The Variable of which this object is the Domain."""
        return self._variable

    @staticmethod
    def remove_value_choice_functions(specific_domain: type) -> None:
        Domain.value_choice_functions[specific_domain] = None

    @staticmethod
    def register_value_choice_function(
        specific_domain: type, vcf: ValueChoiceFunction, name: str
    ) -> None:
        one_class_vcfs = Domain.value_choice_functions.get(specific_domain)
        if one_class_vcfs is None:
            one_class_vcfs = {}
            Domain.value_choice_functions[specific_domain] = one_class_vcfs
        one_class_vcfs[name] = vcf

    def choose_value(self, vcf: str | None = None) -> Any:
        """Choose a value from this Domain.

        With no argument, uses the default ValueChoiceFunction (or the first
        one registered if no default is set) -- merges Java's
        ``chooseValue()``/``chooseValue(String)`` overloads.
        """
        cls = type(self)
        if cls not in Domain.value_choice_functions:
            raise RuntimeError(
                f"No value choice function defined for domains of type {cls.__name__}"
            )
        vcfs = Domain.value_choice_functions[cls]
        if vcfs is None:
            raise RuntimeError(
                f"No value choice function defined for domains of type {cls.__name__}"
            )
        if vcf is None:
            vcf = (
                self.default_value_choice_function
                if self.default_value_choice_function
                else next(iter(vcfs))
            )
        vcfunc = vcfs.get(vcf)
        if vcfunc is None:
            raise IllegalValueChoiceFunction(vcf, cls.__name__)
        return vcfunc.get_value(self)

    def set_default_value_choice_function(self, vcf: str) -> None:
        self.default_value_choice_function = vcf

    def get_value_choice_functions(
        self, specific_domain: type
    ) -> dict[str, ValueChoiceFunction] | None:
        return Domain.value_choice_functions.get(specific_domain)

    @abstractmethod
    def __str__(self) -> str: ...
