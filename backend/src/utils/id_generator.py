"""
Universal Row ID Generator for Quantitative Data Layer

Implements standardized row_id generation following the pattern:
row_id = {grain_keys}#{hash8}

This ensures:
- Cross-table traceability
- Deterministic ID generation
- Collision resistance
- Compact representation
"""

import hashlib
import json
from typing import Dict, List, Any, Union
from datetime import datetime


class RowIDGenerator:
    """Generates standardized row_id following {grain_keys}#{hash8} pattern"""

    @staticmethod
    def generate_hash8(content: str) -> str:
        """Generate 8-character hash from content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:8]

    @staticmethod
    def serialize_value(value: Any) -> str:
        """Serialize value for consistent hashing"""
        if value is None:
            return "null"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return value
        elif isinstance(value, datetime):
            return str(int(value.timestamp()))
        elif isinstance(value, (list, tuple)):
            return ",".join(str(v) for v in value)
        elif isinstance(value, dict):
            return json.dumps(value, sort_keys=True, separators=(',', ':'))
        else:
            return str(value)

    @classmethod
    def generate_row_id(cls, grain_fields: Dict[str, Any], extra_data: Dict[str, Any] = None) -> str:
        """
        Generate standardized row_id

        Args:
            grain_fields: Primary grain key-value pairs (e.g., {"match_id": "NA1_123", "puuid": "abc"})
            extra_data: Additional data for hash generation (optional)

        Returns:
            Formatted row_id: "NA1_123#abc#d4f5b2e8"
        """
        # Build grain key portion
        grain_values = []
        for key in sorted(grain_fields.keys()):  # Deterministic order
            value = grain_fields[key]
            serialized = cls.serialize_value(value)
            grain_values.append(serialized)

        grain_portion = "#".join(grain_values)

        # Build hash content (grain + extra data)
        hash_content = grain_portion
        if extra_data:
            extra_content = json.dumps(extra_data, sort_keys=True, separators=(',', ':'))
            hash_content += f"|{extra_content}"

        # Generate hash8
        hash8 = cls.generate_hash8(hash_content)

        # Combine: {grain_keys}#{hash8}
        return f"{grain_portion}#{hash8}"


class SchemaRowIDGenerators:
    """Pre-configured row_id generators for each schema"""

    @staticmethod
    def fact_participant(match_id: str, puuid: str, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for FactParticipant"""
        return RowIDGenerator.generate_row_id(
            grain_fields={"match_id": match_id, "puuid": puuid},
            extra_data=extra_data
        )

    @staticmethod
    def fact_match(match_id: str, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for FactMatch"""
        return RowIDGenerator.generate_row_id(
            grain_fields={"match_id": match_id},
            extra_data=extra_data
        )

    @staticmethod
    def dim_player(puuid: str, valid_from: datetime, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for DimPlayer (SCD2)"""
        return RowIDGenerator.generate_row_id(
            grain_fields={"puuid": puuid, "valid_from": valid_from},
            extra_data=extra_data
        )

    @staticmethod
    def dim_champion(champion_id: int, patch: str, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for DimChampion"""
        return RowIDGenerator.generate_row_id(
            grain_fields={"champion_id": champion_id, "patch": patch},
            extra_data=extra_data
        )

    @staticmethod
    def dim_item(item_id: int, patch: str, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for DimItem"""
        return RowIDGenerator.generate_row_id(
            grain_fields={"item_id": item_id, "patch": patch},
            extra_data=extra_data
        )

    @staticmethod
    def metric_efp(patch: str, champion_id: int, role: str, item_set_hash: str, extra_data: Dict[str, Any] = None) -> str:
        """Generate row_id for MetricEFP"""
        return RowIDGenerator.generate_row_id(
            grain_fields={
                "patch": patch,
                "champion_id": champion_id,
                "role": role,
                "item_set_hash": item_set_hash
            },
            extra_data=extra_data
        )


def generate_item_set_hash(items: List[int]) -> str:
    """Generate standardized item set hash for core build (items 0-2)"""
    # Take first 3 items (core build), sort for consistency
    core_items = sorted([item for item in items[:3] if item != 0])
    content = ",".join(str(item) for item in core_items)
    return RowIDGenerator.generate_hash8(content)


# Usage examples for testing
if __name__ == "__main__":
    from datetime import datetime

    # Test FactParticipant
    participant_id = SchemaRowIDGenerators.fact_participant(
        match_id="NA1_4898851234",
        puuid="abc123def456",
        extra_data={"champion_id": 161, "role": "ADC"}
    )
    print(f"FactParticipant: {participant_id}")

    # Test FactMatch
    match_id = SchemaRowIDGenerators.fact_match(
        match_id="NA1_4898851234",
        extra_data={"patch": "15.19.1", "queue_id": 420}
    )
    print(f"FactMatch: {match_id}")

    # Test DimPlayer (SCD2)
    player_id = SchemaRowIDGenerators.dim_player(
        puuid="abc123def456",
        valid_from=datetime(2024, 9, 15, 10, 30, 0),
        extra_data={"tier": "DIAMOND", "division": "II"}
    )
    print(f"DimPlayer: {player_id}")

    # Test MetricEFP
    item_hash = generate_item_set_hash([3006, 3031, 3094, 0, 0, 0, 3340])  # Core ADC build
    efp_id = SchemaRowIDGenerators.metric_efp(
        patch="15.19.1",
        champion_id=161,
        role="ADC",
        item_set_hash=item_hash,
        extra_data={"sample_size": 1500}
    )
    print(f"MetricEFP: {efp_id}")
    print(f"Item Set Hash: {item_hash}")