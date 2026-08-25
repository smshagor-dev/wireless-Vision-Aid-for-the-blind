#!/usr/bin/env python3
"""Compatibility entrypoint for the WVAB secure UDP runtime.

The wrapper also applies the canonical mobility-class policy so generic COCO
labels such as ``traffic light`` and custom WVAB labels such as
``traffic_light`` have identical filtering/priority behavior.
"""

from core import udp_runtime as _runtime
from core.object_policy import CriticalObjectPolicy, label_candidates


SimpleTracker = _runtime.SimpleTracker
UDPCameraClient = _runtime.UDPCameraClient
_build_parser = _runtime._build_parser
_derive_nonce = _runtime._derive_nonce
_new_session_id = _runtime._new_session_id
_secure_transport_settings = _runtime._secure_transport_settings


class UDPVisionServer(_runtime.UDPVisionServer):
    """Secure UDP server with normalized mobility hazard filtering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.critical_objects = CriticalObjectPolicy()

    def _translate(self, class_name, language=None):
        language = language or self.language
        for candidate in label_candidates(class_name):
            entry = self.multilingual_labels.get(candidate)
            if isinstance(entry, dict):
                return entry.get(language, entry.get("en", candidate.replace("_", " ")))
        return str(class_name or "object").replace("_", " ")


def main():
    # core.udp_runtime owns argument parsing/restart/session logic. Temporarily
    # supply the policy-aware subclass so every supported source-checkout,
    # systemd, Docker, and main.py launch path gets the same object policy.
    original = _runtime.UDPVisionServer
    _runtime.UDPVisionServer = UDPVisionServer
    try:
        return _runtime.main()
    finally:
        _runtime.UDPVisionServer = original


__all__ = [
    "SimpleTracker",
    "UDPCameraClient",
    "UDPVisionServer",
    "_build_parser",
    "_derive_nonce",
    "_new_session_id",
    "_secure_transport_settings",
    "main",
]


if __name__ == "__main__":
    main()
