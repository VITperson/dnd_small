"""Party builder utilities for assembling a small RPG party following strict template rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Iterable, Optional
import json


STAT_KEYS: List[str] = ["str", "dex", "int", "wit", "charm"]
MIN_STAT = -1
MAX_STAT = 3
MIN_HP = 8
MAX_HP = 14


class PartyValidationError(ValueError):
    """Raised when party data violates the template restrictions."""


@dataclass
class PartyMember:
    """Represents a single party member adhering to the required template."""

    id: str
    name: str
    role: str
    concept: str
    stats: Dict[str, int]
    traits: List[str]
    loadout: List[str]
    hp: int
    tags: List[str] = field(default_factory=list)

    def validate(self) -> None:
        """Validate member data against the template rules."""
        if not self.id:
            raise PartyValidationError("Member id must be provided.")
        if not self.name:
            raise PartyValidationError("Member name must be provided.")
        if not self.role:
            raise PartyValidationError("Member role must be provided.")
        if not self.concept:
            raise PartyValidationError("Member concept must be provided.")

        if set(self.stats.keys()) != set(STAT_KEYS):
            raise PartyValidationError(
                f"Stats must include exactly the keys: {', '.join(STAT_KEYS)}"
            )

        for key, value in self.stats.items():
            if not isinstance(value, int):
                raise PartyValidationError(f"Stat '{key}' must be an integer.")
            if value < MIN_STAT or value > MAX_STAT:
                raise PartyValidationError(
                    f"Stat '{key}' must be between {MIN_STAT} and {MAX_STAT}."
                )

        if len(self.traits) != 2:
            raise PartyValidationError("Member must have exactly 2 traits.")
        if len(self.loadout) != 2:
            raise PartyValidationError("Member must have exactly 2 loadout items.")
        if any(not item for item in self.traits):
            raise PartyValidationError("Trait descriptions cannot be empty.")
        if any(not item for item in self.loadout):
            raise PartyValidationError("Loadout items cannot be empty.")

        if not isinstance(self.hp, int):
            raise PartyValidationError("HP must be an integer.")
        if self.hp < MIN_HP or self.hp > MAX_HP:
            raise PartyValidationError(f"HP must be between {MIN_HP} and {MAX_HP}.")

        if not (0 < len(self.tags) <= 2):
            raise PartyValidationError("Member must have 1 or 2 tags.")
        if any(not tag for tag in self.tags):
            raise PartyValidationError("Tags cannot be empty strings.")


class PartyBuilder:
    """Builds a party payload compliant with the required output schema."""

    MAX_MEMBERS = 3

    def __init__(
        self,
        coin: int = 0,
        rations: int = 0,
        party_tags: Optional[Iterable[str]] = None,
    ):
        self._members: List[PartyMember] = []
        self.coin = coin
        self.rations = rations
        self.party_tags = [tag for tag in (party_tags or []) if tag][:3]

    @property
    def members(self) -> List[PartyMember]:
        """Immutable view of the current members list."""
        return list(self._members)

    def add_member(self, member: PartyMember) -> None:
        """Add a member to the party after validating constraints."""
        if len(self._members) >= self.MAX_MEMBERS:
            raise PartyValidationError("Party already has the maximum number of members.")

        if any(existing.id == member.id for existing in self._members):
            raise PartyValidationError(f"Member with id '{member.id}' already exists.")

        member.validate()
        self._members.append(member)

    def is_full(self) -> bool:
        """Return True if the party reached the maximum size."""
        return len(self._members) >= self.MAX_MEMBERS

    def clear(self) -> None:
        """Remove all members from the party."""
        self._members.clear()

    def build_payload(self) -> Dict[str, object]:
        """Return the complete payload matching the specified JSON schema."""
        members_payload = [self._member_to_payload(member) for member in self._members]
        compact = [self._member_to_compact(member) for member in self._members]

        return {
            "party": {
                "max_size": self.MAX_MEMBERS,
                "members": members_payload,
                "resources": {"coin": self.coin, "rations": self.rations},
                "party_tags": self.party_tags,
            },
            "state_delta": {
                "flags": {"set": ["party_initialized"]},
                "inventory_add": [{"owner": "party", "item_id": "basic_kit"}],
            },
            "party_compact": compact,
        }

    def build_payload_json(self, *, indent: int = 2) -> str:
        """Return the payload as a JSON string."""
        payload = self.build_payload()
        return json.dumps(payload, ensure_ascii=False, indent=indent)

    def _member_to_payload(self, member: PartyMember) -> Dict[str, object]:
        """Convert a PartyMember to the dictionary required by the schema."""
        return {
            "id": member.id,
            "name": member.name,
            "role": member.role,
            "concept": member.concept,
            "stats": member.stats,
            "traits": member.traits,
            "loadout": member.loadout,
            "hp": member.hp,
            "tags": member.tags,
        }

    def _member_to_compact(self, member: PartyMember) -> str:
        """Create the compact string representation for the member."""
        key_stat = self._determine_key_stat(member.stats)
        key_value = member.stats[key_stat]
        value_str = f"{key_stat.upper()}{key_value:+d}"
        items = ", ".join(member.loadout)
        traits = ", ".join(member.traits)
        return f"{member.name}-{member.role} {value_str} HP{member.hp} - {items}; черты: {traits}"

    @staticmethod
    def _determine_key_stat(stats: Dict[str, int]) -> str:
        """Choose the primary stat based on the highest value and predefined priority."""
        priority = {key: index for index, key in enumerate(STAT_KEYS)}
        return max(STAT_KEYS, key=lambda key: (stats[key], -priority[key]))


__all__ = ["PartyBuilder", "PartyMember", "PartyValidationError"]
