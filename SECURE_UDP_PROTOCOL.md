# WVAB Secure UDP Protocol

This document describes the transport used by `udp_streaming.py` / `core/udp_runtime.py` and `esp32_cam_stream.ino` on the same source revision. The peers must use compatible revisions; the older 10-byte packet format is intentionally rejected after session/replay hardening.

## Security scope

The supported deployment path uses:

- AES-GCM with a deployment-specific 16, 24, or 32-byte key
- a deployment-specific authentication token of at least 16 characters
- a fresh non-zero 32-bit session ID for every sender process/ESP32 boot
- a fresh 96-bit random base nonce for every authentication packet and every video frame
- the complete packet header as AES-GCM Additional Authenticated Data (AAD)
- bounded authentication-nonce replay memory during the server process lifetime
- retired-session rejection after a sender changes session
- monotonically ordered 32-bit frame serials within each authenticated session
- wrap-aware frame replay rejection
- bounded chunks, frame bytes, authenticated clients, and per-client in-flight frames

The transport provides confidentiality and integrity on the local UDP link. It is not a substitute for secure device provisioning, key rotation, physical security, or a VPN when traffic crosses an untrusted routed network.

## Header

Every datagram starts with a 14-byte network-byte-order header:

| Field | Size | Description |
| --- | ---: | --- |
| `session_id` | 4 bytes | Fresh non-zero sender-process/boot identifier. |
| `frame_id` | 4 bytes | Video frame serial. `0xFFFFFFFF` is reserved for authentication. |
| `total_chunks` | 2 bytes | Number of chunks in the video frame; zero for authentication. |
| `chunk_index` | 2 bytes | Zero-based chunk index; zero for authentication. |
| `payload_size` | 2 bytes | Bytes after the header in this datagram. |

For every encrypted datagram, these exact 14 bytes are passed to AES-GCM as AAD. Changing the session ID, frame ID, chunk count, chunk index, or payload size invalidates the GCM tag.

`session_id=0` is invalid. The Python client generates a random non-zero uint32 when the client object is created; the ESP32 generates one with `esp_random()` at boot. Authentication refreshes keep the same session ID. A reboot/new sender gets a new session ID, so its frame counter may safely restart at zero without being mistaken for a replay of the previous session.

## Encrypted authentication datagram

Authentication uses:

```text
header(session_id, frame_id=0xFFFFFFFF, total_chunks=0, chunk_index=0)
base_nonce[12]
tag[16]
ciphertext[token_length]
```

The server authenticates the complete header and token, compares the token using constant-time secret comparison, and rejects an authentication nonce already seen within its bounded replay cache.

A valid authentication packet binds the UDP source address/port to the authenticated `session_id`. A later valid authentication packet for a new session retires the old session for that source. Authentication refresh using the current session renews its TTL without resetting frame replay state.

Previously retired sessions are rejected during the server process lifetime. Server restart resets this in-memory replay history; deployments requiring replay continuity across server restarts need an external authenticated tunnel or persistent anti-replay state.

## Encrypted video datagram

Each chunk uses:

```text
header(session_id, frame_id, total_chunks, chunk_index)
base_nonce[12]
tag[16]
ciphertext[chunk_plaintext_length]
```

Every chunk carries the same frame base nonce. The actual GCM nonce is derived by adding `chunk_index` to the final 32 bits of that base nonce. Because every chunk includes the base nonce, datagram reordering does not require chunk zero to arrive first.

The receiver requires every chunk for a frame to use the same base nonce and authenticates each chunk independently before buffering plaintext. A video packet is accepted only when its source address and `session_id` match the currently authenticated session.

## Replay and resource bounds

The canonical constants are defined in `core/udp_protocol.py` and mirrored in the ESP32 firmware where applicable:

- header size: 14 bytes
- maximum datagram: 1450 bytes
- maximum chunks per frame: 1024
- maximum reconstructed frame: 2 MiB
- maximum in-flight frames per authenticated client/session: 8
- maximum authenticated clients retained by the runtime: 128
- authentication frame ID: `0xFFFFFFFF`
- maximum video frame ID: `0xFFFFFFFE`

Replay tracking is keyed by source address plus authenticated session. After a frame is completed, an equal or older frame serial in that session is rejected. Serial comparison is wrap-aware, so `0` is newer than `0xFFFFFFFE` after a valid wrap.

Incomplete frames expire quickly. Old sessions are removed from active state and retained in a bounded retired-session cache so a captured old authentication packet cannot replace a newer live session during the same server process.

The server watchdog is based on completed/decodeable video frames, not merely valid authentication or chunk traffic. This prevents a sender that only refreshes authentication or sends incomplete chunks from keeping a dead video stream falsely healthy.

## Development exceptions

Authentication and encryption are both required by default. `WVAB_ALLOW_INSECURE_UDP=1` permits isolated development exceptions only and must not be used for a wearable/field deployment.

The release ESP32 firmware has no unauthenticated MJPEG fallback. Use `vision_server.py` only for a local or explicitly trusted IP-camera source when secure ESP32 UDP is not the transport being tested.

## Pairing

Generate a matched pair:

```bash
python tools/generate_device_secrets.py --server-ip 192.168.4.2
```

This creates the git-ignored files:

- `esp32_secrets.h`
- `deployment/rpi/wvab_edge.env`

Flash `esp32_cam_stream.ino` with that generated header and start the Raspberry Pi edge server from the same compatible source revision.
