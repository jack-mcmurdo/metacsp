"""Port of util/MultiListParser.java from the meta-csp-tutorial repo (M23).

Demo-support code (a tiny recursive s-expression tokenizer used by
``parsing.py`` to read the tutorial's ``specification*.txt`` mini-language),
not library code -- not added to PLAN.md's Module map.
"""

from __future__ import annotations

__all__ = ["MultiListParser"]


class MultiListParser:
    def __init__(self, to_parse: str) -> None:
        self.s = to_parse

    def _parse(self) -> list[object]:
        new_list: list[object] = []
        while len(self.s) > 0:
            index_of_space = self.s.find(" ")
            index_of_par_close = self.s.find(")")
            index_of_par_open = self.s.find("(")
            candidates = [
                i for i in (index_of_space, index_of_par_open, index_of_par_close) if i != -1
            ]
            piece_len = max(1, min(candidates)) if candidates else max(1, len(self.s))
            piece = self.s[:piece_len]
            self.s = self.s[len(piece) :]
            if piece == "(":
                new_list.append(self._parse())
            elif piece == ")":
                break
            elif piece == " ":
                pass
            else:
                new_list.append(piece)
        return new_list

    def parse_objects(self) -> list[object]:
        ret = self._parse()
        if not ret or len(ret) > 1:
            return ret
        return ret[0]  # type: ignore[return-value]
