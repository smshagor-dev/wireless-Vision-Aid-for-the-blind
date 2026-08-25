import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class SafetyState:
    state: str
    reason: str
    timestamp: float
    metadata: dict[str, Any]


class SafetyStatePublisher:
    """Fail-safe state output for assistive navigation consumers.

    This does not command a motor. It publishes an atomic machine-readable state
    that an audio/haptic/device adapter can consume. Unknown or unavailable
    perception/localization must publish STOP/DEGRADED rather than imply safety.
    """

    def __init__(self, path: str):
        if not path:
            raise ValueError("safety state path is required")
        self.path = path

    def publish(self, state: str, reason: str, **metadata: Any) -> SafetyState:
        normalized = str(state).strip().upper()
        if normalized not in {"STOP", "DEGRADED", "GUIDANCE_AVAILABLE"}:
            raise ValueError(f"unsupported safety state: {state}")
        value = SafetyState(
            state=normalized,
            reason=str(reason),
            timestamp=time.time(),
            metadata=metadata,
        )
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(asdict(value), handle, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, self.path)
        return value

    def stop(self, reason: str, **metadata: Any) -> SafetyState:
        return self.publish("STOP", reason, **metadata)

    def degraded(self, reason: str, **metadata: Any) -> SafetyState:
        return self.publish("DEGRADED", reason, **metadata)

    def guidance(self, reason: str = "path_available", **metadata: Any) -> SafetyState:
        return self.publish("GUIDANCE_AVAILABLE", reason, **metadata)
