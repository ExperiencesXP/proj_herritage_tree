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
    DEFAULT_NAMES: ClassVar[dict[str, str]] = {
        "male": "John Doe",
        "female": "Jane Doe",
        "other": "An Other",
        "they": "Alex Doe",
    }

    def __init__(
        self,
        name: str | None = None,
        mom: Person | None = None,
        dad: Person | None = None,
        pronouns: Pronouns | None = None,
    ):
        self.mom = mom
        self.dad = dad
        self.name = name if name is not None else self.default_name(pronouns)
        self.pronouns = pronouns or Pronouns.from_preset("they")

    @classmethod
    def default_name(cls, pronouns: Pronouns | None) -> str:
        if pronouns is None:
            return cls.DEFAULT_NAMES["they"]
        for key, preset in Pronouns.PRESETS.items():
            if pronouns is preset:
                return cls.DEFAULT_NAMES.get(key, cls.DEFAULT_NAMES["other"])
        return cls.DEFAULT_NAMES["other"]

    def __str__(self) -> str:
        known: list[str] = []
        if self.mom:
            known.append(f"mother is {self.mom.name}")
        if self.dad:
            known.append(f"father is {self.dad.name}")

        if not known:
            return f"{self.name} has no known parents."
        if len(known) == 1:
            known.append("no known father" if self.mom else "no known mother")

        return f"{self.name}'s " + " and ".join(known) + "."

    def pronoun(self, form: str) -> str:
        return self.pronouns.get(form)
