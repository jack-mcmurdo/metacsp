"""Port of util/Parsing.java from the meta-csp-tutorial repo (M23).

Demo-support code (a spec-file mini-language reader used only by the
tutorial demos), not library code -- not added to PLAN.md's Module map.
Java's ``static`` fields become module-level globals here.
"""

from __future__ import annotations

from typing import Any

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

from util.multi_list_parser import MultiListParser

__all__ = ["set_variable_factory", "parse_specification", "load_specification"]

ans: ActivityNetworkSolver | None = None
ids_to_vars: dict[str, SymbolicVariableActivity] = {}
specification_counter: int = 0


def set_variable_factory(solver: ActivityNetworkSolver) -> None:
    global ans
    ans = solver


def process_bounds(bounds: str) -> Bounds:
    # "[lb,ub]" -> Bounds(lb, ub), with "INF"/"-INF" mapped to +/-APSPSolver.INF.
    no_par = bounds[bounds.index("[") + 1 : bounds.index("]")]
    no_par = no_par.replace(" ", "").replace("\t", "")
    two_nums = no_par.split(",")

    def parse_one(token: str) -> int:
        if "INF" in token:
            return -APSPSolver.INF if token.startswith("-") else APSPSolver.INF
        return int(token)

    return Bounds(parse_one(two_nums[0]), parse_one(two_nums[1]))


def make_constraint(objs: list[Any]) -> AllenIntervalConstraint:
    # (Constraint type varFromId varToId [lb,ub] ... [lb,ub])
    type_s = objs[1]
    type_ = AllenIntervalConstraint.Type.from_string(type_s)
    assert type_ is not None
    act_from = ids_to_vars[f"{objs[2]}__{specification_counter}"]
    act_to = ids_to_vars[f"{objs[3]}__{specification_counter}"]
    bounds = [process_bounds(b) for b in objs[4:]]
    con = AllenIntervalConstraint(type_) if not bounds else AllenIntervalConstraint(type_, *bounds)
    con.from_ = act_from
    con.to = act_to
    return con


def make_variable(objs: list[Any]) -> SymbolicVariableActivity:
    global specification_counter
    assert ans is not None
    id_ = objs[1]
    values = [str(o) for o in objs[2:-1]]
    component = objs[-1]
    act = ans.create_variable(component)
    assert isinstance(act, SymbolicVariableActivity)
    act.set_symbolic_domain(*values)
    ids_to_vars[f"{id_}__{specification_counter}"] = act
    return act


def parse_specification(spec: str) -> ConstraintNetwork:
    global specification_counter
    ret = ConstraintNetwork(None)
    objs = MultiListParser(spec).parse_objects()
    for oneline in objs:
        if oneline and isinstance(oneline[0], str):
            one_line_type = oneline[0]
            if one_line_type == "Constraint":
                ret.add_constraint(make_constraint(oneline))
            elif one_line_type == "Variable":
                ret.add_variable(make_variable(oneline))
    specification_counter += 1
    return ret


def load_specification(filename: str) -> ConstraintNetwork:
    spec = ""
    with open(filename) as f:
        for line in f:
            if not line.startswith("#") and line.strip() != "":
                spec += line.rstrip("\n")
    return parse_specification(spec)
