from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FieldCandidate:
    source_type: str
    source_file: str
    source_sheet: str
    source_column: str
    raw_value: Any
    normalized_value: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_file": self.source_file,
            "source_sheet": self.source_sheet,
            "source_column": self.source_column,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "FieldCandidate":
        return cls(
            source_type=str(value.get("source_type") or ""),
            source_file=str(value.get("source_file") or ""),
            source_sheet=str(value.get("source_sheet") or ""),
            source_column=str(value.get("source_column") or ""),
            raw_value=value.get("raw_value"),
            normalized_value=value.get("normalized_value"),
            confidence=float(value.get("confidence", 1.0)),
            metadata=value.get("metadata") if isinstance(value.get("metadata"), dict) else {},
        )


@dataclass
class FieldRuntime:
    field_key: str
    value: Any
    status: str
    candidates: List[FieldCandidate] = field(default_factory=list)
    selected_index: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_key": self.field_key,
            "value": self.value,
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_index": self.selected_index,
        }

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "FieldRuntime":
        candidates = [
            FieldCandidate.from_dict(candidate)
            for candidate in value.get("candidates", [])
            if isinstance(candidate, dict)
        ]
        return cls(
            field_key=str(value.get("field_key") or ""),
            value=value.get("value"),
            status=str(value.get("status") or "missing"),
            candidates=candidates,
            selected_index=int(value.get("selected_index", -1)),
        )
