"""Repository model grouping ordered rulesets for one service."""

from knowledgenet.ruleset import Ruleset

class Repository:
    """Defines a named repository with executable rulesets.

    Service executes rulesets in listed order unless flow-control actions
    request early termination or switching to a specific ruleset.
    """

    def __init__(self, id: str, rulesets: list[Ruleset]) -> None:
        self.id = id
        self.rulesets = rulesets

    def __str__(self) -> str:
        return f"Repository({self.id})"

    def __repr__(self) -> str:
        return self.__str__()
