"""Family data model: `Person` / `Pronouns` (docs/cluster_map_and_recursive_search.md §1).

``V`` in the design doc is the population of :class:`Person` objects; ``Person.mom`` /
``Person.dad`` are the two parental edges (invariant **I1**: ``deg⁻(v) ≤ 2``, so
``m = |E| ≤ 2n``).  ``Person.name`` is the natural key used by external maps and Mermaid
labels.  The presentation helpers (``__str__``, ``pronoun``) play no role in the algorithms
and live here so the graph modules stay presentation-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Pronouns:
    subject: str
    object: str
    possessive_adjective: str
    possessive_pronoun: str
    reflexive: str

    PRESETS: ClassVar[dict[str, Pronouns]] = {}

    @classmethod
    def from_preset(cls, name: str) -> Pronouns:
        try:
            return cls.PRESETS[name.lower()]
        except KeyError as error:
            raise ValueError(f"Unknown pronoun preset: {name}") from error

    def get(self, form: str) -> str:
        try:
            return getattr(self, form.lower())
        except AttributeError as error:
            valid_forms = ", ".join(
                (
                    "subject",
                    "object",
                    "possessive_adjective",
                    "possessive_pronoun",
                    "reflexive",
                )
            )
            raise ValueError(
                f"Unknown pronoun form: {form}. Use: {valid_forms}"
            ) from error


Pronouns.PRESETS.update(
    {
        "male": Pronouns("he", "him", "his", "his", "himself"),
        "female": Pronouns("she", "her", "her", "hers", "herself"),
        "other": Pronouns("they", "them", "their", "theirs", "themselves"),
        "they": Pronouns("they", "them", "their", "theirs", "themselves"),
    }
)


class Person:
    def __init__(
        self,
        name: str = "John Doe",
        mom: Person | None = None,
        dad: Person | None = None,
        pronouns: Pronouns | None = None,
    ):
        self.mom = mom
        self.dad = dad
        self.name = name
        self.pronouns = pronouns or Pronouns.from_preset("they")

    def __str__(self) -> str:
        parent_line: list[str] = []
        if self.mom:
            parent_line.append(f"mother is {self.mom.name}")
        if self.dad:
            parent_line.append(f"father is {self.dad.name}")
        if len(parent_line) == 1:
            if self.mom:
                parent_line.append("no known mother")
            else:
                parent_line.append("no known father")

        if not parent_line:
            parent_line.append(f"{self.pronouns.subject} has no known parents")

        parents = " and ".join(parent_line)
        return f"{self.name}'s {parents}."

    def pronoun(self, form: str) -> str:
        return self.pronouns.get(form)
