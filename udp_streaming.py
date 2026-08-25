#!/usr/bin/env python3
"""Compatibility entrypoint for the WVAB secure UDP runtime."""

from core.udp_runtime import (
    SimpleTracker,
    UDPCameraClient,
    UDPVisionServer,
    _build_parser,
    _derive_nonce,
    _new_session_id,
    _secure_transport_settings,
    main,
)

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
