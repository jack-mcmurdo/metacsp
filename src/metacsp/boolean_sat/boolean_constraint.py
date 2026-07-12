"""Port of booleanSAT/BooleanConstraint.java.

``create_boolean_constraints`` implements D6: the WFF is tokenized and
translated into a sympy boolean expression (``~``->``Not``, ``^``->``And``,
``v``->``Or``, ``->``->``Implies``, ``<->``->``Equivalent``), converted to
CNF with ``sympy.logic.boolalg.to_cnf(expr, simplify=False)``, and one
BooleanConstraint is emitted per CNF clause -- mirroring the Java factory
(which used the aima-core library) clause for clause, including its
same-clause literal-cancellation and subsumption checks.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import sympy
from sympy.logic.boolalg import And, Equivalent, Implies, Not, Or, to_cnf

from metacsp.framework.constraint import Constraint

if TYPE_CHECKING:
    from metacsp.boolean_sat.boolean_variable import BooleanVariable

__all__ = ["BooleanConstraint"]

_MALFORMED_MESSAGE = (
    "Malformed BooleanConstraint - allowed logical connectives:\n"
    "\t^ : AND\n\tv : OR\n\t-> : implication\n\t<-> : iff\n\t~ : NOT"
)

# `v` is an operator token, so variable placeholders are matched as <letter><digits>
# only. The Java parser accepts any single-letter prefix (it recovers the index via
# `lit.toString().substring(1)`, dropping exactly one leading character regardless of
# which letter it is) -- e.g. SymbolicVariable generates WFFs using "w1", "w2", ...
# rather than "x1", "x2", .... Mirrored here the same way: match any single-letter
# prefix, and later resolve the index by stripping just the first character.
_TOKEN_RE = re.compile(r"<->|->|[()^~]|v|[a-zA-Z]\d+")


def _tokenize(wff: str) -> list[str]:
    return _TOKEN_RE.findall(wff)


class _WffParser:
    """Recursive-descent parser for the fully-parenthesized WFF grammar:
    ``expr := <letter> digits | '~' expr | '(' expr op expr ')'``."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.var_symbols: dict[str, sympy.Symbol] = {}

    def _var_symbol(self, token: str) -> sympy.Symbol:
        if token not in self.var_symbols:
            self.var_symbols[token] = sympy.Symbol(token)
        return self.var_symbols[token]

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> str:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def parse(self) -> sympy.Basic:
        expr = self._parse_expr()
        if self.pos != len(self.tokens):
            raise ValueError("trailing tokens in WFF")
        return expr

    def _parse_expr(self) -> sympy.Basic:
        t = self._peek()
        if t == "~":
            self._next()
            return Not(self._parse_expr())
        if t == "(":
            self._next()
            left = self._parse_expr()
            if self._peek() == ")":
                # A redundant parenthesized sub-expression with no operator,
                # e.g. "(x1)" -- Java's aima-based parser accepts these too.
                self._next()
                return left
            op = self._next()
            right = self._parse_expr()
            if self._next() != ")":
                raise ValueError("expected closing parenthesis")
            if op == "^":
                return And(left, right)
            if op == "v":
                return Or(left, right)
            if op == "->":
                return Implies(left, right)
            if op == "<->":
                return Equivalent(left, right)
            raise ValueError(f"unknown operator {op}")
        if t is not None and re.fullmatch(r"[a-zA-Z]\d+", t):
            self._next()
            return self._var_symbol(t)
        raise ValueError(f"unexpected token {t}")


class BooleanConstraint(Constraint):
    """A disjunctive Boolean clause, e.g. ``(x1 v x2 v ~x3)``."""

    def __init__(self, scope: list[BooleanVariable], positive: list[bool]) -> None:
        super().__init__()
        self.positive = positive
        self.scope = list(scope)

    @staticmethod
    def create_boolean_constraints(
        scope: list[BooleanVariable], wff: str
    ) -> list[BooleanConstraint]:
        """Factory creating BooleanConstraints (one per CNF clause) from an
        arbitrary propositional logic formula over placeholders x1..xN bound
        positionally to ``scope``."""
        try:
            tokens = _tokenize(wff)
            expr = _WffParser(tokens).parse()
            cnf = to_cnf(expr, simplify=False)
        except Exception as e:
            raise RuntimeError(_MALFORMED_MESSAGE) from e

        clauses = cnf.args if isinstance(cnf, And) else (cnf,)

        cons: list[BooleanConstraint] = []
        for clause in clauses:
            literals = clause.args if isinstance(clause, Or) else (clause,)
            positive_syms = [lit for lit in literals if not isinstance(lit, Not)]
            negative_syms = [lit.args[0] for lit in literals if isinstance(lit, Not)]

            new_clause: dict[BooleanVariable, bool] = {}
            for sym in positive_syms:
                bv = scope[int(str(sym)[1:]) - 1]
                new_clause[bv] = True
            for sym in negative_syms:
                bv = scope[int(str(sym)[1:]) - 1]
                if bv in new_clause:
                    del new_clause[bv]
                else:
                    new_clause[bv] = False

            if new_clause:
                relevant_vars = list(new_clause.keys())
                positive_flags = [new_clause[v] for v in relevant_vars]
                bc = BooleanConstraint(relevant_vars, positive_flags)
                if not any(bc.is_equivalent(other) for other in cons):
                    cons.append(bc)
        return cons

    def get_literals(self) -> list[int]:
        """DIMACS literals for this clause: BooleanVariable id n -> literal
        n (positive) or -n (negated)."""
        return [
            self.scope[i].id if self.positive[i] else -self.scope[i].id
            for i in range(len(self.scope))
        ]

    def __str__(self) -> str:
        parts = []
        for i, var in enumerate(self.scope):
            bv = var
            parts.append(f"~x{bv.id}" if not self.positive[i] else f"x{bv.id}")
        return "(" + " v ".join(parts) + ")"

    @property
    def edge_label(self) -> str:
        return str(self)

    def clone(self) -> BooleanConstraint:
        ret = BooleanConstraint(list(self.scope), list(self.positive))
        ret.auto_removable = self.auto_removable
        return ret

    def is_equivalent(self, c: Constraint) -> bool:
        if not isinstance(c, BooleanConstraint):
            return False
        if len(self.scope) != len(c.scope):
            return False
        for i in range(len(self.scope)):
            if self.scope[i] != c.scope[i]:
                return False
            if self.positive[i] != c.positive[i]:
                return False
        return True
