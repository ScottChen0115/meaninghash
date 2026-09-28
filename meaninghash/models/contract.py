"""SemanticContract: the central data structure of MeaningHash."""
from __future__ import annotations

from pydantic import BaseModel, Field

from meaninghash.models.requirement import Requirement, RequirementKind


class ContractSource(BaseModel):
    type: str = "document"
    source_id: str = ""
    path: str | None = None


_ID_PREFIX = {
    RequirementKind.GOAL: "G",
    RequirementKind.CONSTRAINT: "C",
    RequirementKind.PERMISSION: "P",
    RequirementKind.PREFERENCE: "PR",
    RequirementKind.ASSUMPTION: "A",
}


def next_requirement_id(kind: RequirementKind, existing: list[str]) -> str:
    prefix = _ID_PREFIX.get(kind, "R")
    used = [rid for rid in existing if rid.startswith(prefix)]
    n = len(used) + 1
    return f"{prefix}{n:03d}"


class SemanticContract(BaseModel):
    """A structured snapshot of the meaning of a document."""

    version: str = "0.1"
    source: ContractSource = Field(default_factory=ContractSource)
    requirements: list[Requirement] = Field(default_factory=list)

    # -- grouped views (Section 7 of the plan) ----------------------------
    @property
    def goals(self) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.GOAL]

    @property
    def constraints(self) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.CONSTRAINT]

    @property
    def permissions(self) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.PERMISSION]

    @property
    def preferences(self) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.PREFERENCE]

    @property
    def assumptions(self) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.ASSUMPTION]

    def of_kind(self, kind: RequirementKind) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == kind]

    def get(self, requirement_id: str) -> Requirement | None:
        for r in self.requirements:
            if r.id == requirement_id:
                return r
        return None

    def summary(self) -> dict[str, int]:
        return {
            "goals": len(self.goals),
            "constraints": len(self.constraints),
            "permissions": len(self.permissions),
            "preferences": len(self.preferences),
            "assumptions": len(self.assumptions),
            "total": len(self.requirements),
        }

    def to_grouped_dict(self) -> dict:
        """Plan-style grouped layout (goals / constraints / permissions / ...)."""

        def group(reqs: list[Requirement]) -> list[dict]:
            return [r.model_dump(mode="json") for r in reqs]

        return {
            "version": self.version,
            "source": self.source.model_dump(mode="json"),
            "goals": group(self.goals),
            "constraints": group(self.constraints),
            "permissions": group(self.permissions),
            "preferences": group(self.preferences),
            "assumptions": group(self.assumptions),
        }

    def total_weight(self) -> int:
        return sum(r.weight for r in self.requirements)
