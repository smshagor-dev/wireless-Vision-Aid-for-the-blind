# WVAB Secure UDP Protocol

This document describes the transport used by `udp_streaming.py` / `core/udp_runtime.py` and `esp32_cam_stream.ino` on the same source revision. The peers must use compatible revisions. The older 10-byte packet format and legacy token-only authentication payload are intentionally rejected after session/replay hardening.

## Security scope

The supported deployment path uses:

- AES-GCM with a deployment-specific 16, 24, or 32-byte key
- a deployment-specific authentication token of at least 16 characters
- a fresh non-zero 32-bit session ID for every sender process/ESP32 boot
- a monotonically increasing 64-bit authentication counter within each sender session
- the sender's next 32-bit video-frame ID bound into every authentication refresh
- a fresh 96-bit random base nonce for every authentication packet and every video frame
- the complete packet header as AES-GCM Additional Authenticated Data (AAD)
- bounded in-memory authentication-nonce replay memory
- bounded persistent authentication-counter state across server/container restarts
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

`session_id=0` is invalid. The Python client generates a random non-zero uint32 when the client object is created; the ESP32 generates one with `esp_random()` at boot. Authentication refreshes keep the same session ID. A reboot/new sender gets a new session ID, so its frame counter may safely restart at zero without being mistaken for a replay of the previous live session.

## Protocol-v2 authentication plaintext

Authentication cleartext is versioned and encrypted with AES-GCM. The v2 plaintext is:

```text
version[1] = 0x02
auth_counter[8]       # uint64, network byte order, starts at 1
next_frame_id[4]      # uint32, network byte order
token[N]              # deployment-specific UTF-8 token
```

The encrypted authentication datagram is:

```text
header(session_id, frame_id=0xFFFFFFFF, total_chunks=0, chunk_index=0)
base_nonce[12]
tag[16]
ciphertext(version | auth_counter | next_frame_id | token)
```

The complete 14-byte header is authenticated as GCM AAD. Legacy token-only authentication payloads are rejected rather than silently downgraded.

The server verifies the GCM tag and token, then records the highest accepted `auth_counter` for that `session_id` in persistent replay state **before** granting or renewing the session. The same or a lower authentication counter is rejected even after the Python process or Docker container restarts, provided the replay-state file/volume is preserved.

`next_frame_id` is the sender's next video frame serial at the moment the authentication packet is created. The receiver establishes the completed-frame replay baseline as the immediately preceding serial. For example, `next_frame_id=50` establishes a baseline of `49`. `next_frame_id=0` establishes a wrap-aware baseline of `0xFFFFFFFE`.

A delayed authentication refresh may have a higher authentication counter but an older frame baseline. The server records its counter so the packet cannot be replayed later, but refuses to move the current frame replay baseline backwards.

## Persistent replay state

The default source-checkout/Raspberry Pi state path is:

```text
state/udp_replay_state.json
```

It can be changed with `WVAB_UDP_REPLAY_STATE_PATH`. `tools/generate_device_secrets.py` configures the Raspberry Pi environment to use this path. Docker Compose overrides it to `/var/lib/wvab/udp_replay_state.json` and mounts the `wvab-replay-state` named volume so the state survives normal container restarts/recreation.

The persisted file contains session IDs, highest accepted authentication counters, and their latest next-frame baselines. It does **not** contain the AES key or authentication token. Writes are atomic, fsynced, and permission-restricted where the host supports POSIX file modes. Malformed/corrupt state fails closed rather than being silently discarded.

The persistent store is intentionally bounded (`WVAB_UDP_REPLAY_MAX_SESSIONS`, default 4096). Credential rotation remains part of normal deployment maintenance.

If the replay-state file/volume is intentionally deleted, lost, rolled back, or restored from an older backup, rotate/re-pair the deployment key and token before resuming a field deployment. Losing this state removes the server's memory of previously accepted authentication counters and can make a captured historical authentication packet eligible again if the same long-lived credentials are reused.

## Session binding

A valid authentication packet binds the UDP source address/port to the authenticated `session_id`. A later valid authentication packet for a new session retires the old session for that source. Authentication refresh using the current session renews its TTL without resetting the completed-frame replay state.

In-memory retired-session and authentication-nonce caches remain bounded additional defenses. Persistent auth-counter state is the mechanism that carries authentication replay protection across normal server restarts.

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

After a frame is completed, an equal or older frame serial in that session is rejected. Serial comparison is wrap-aware, so `0` is newer than `0xFFFFFFFE` after a valid wrap. A later protocol-v2 authentication refresh may advance this replay baseline but may never move it backwards.

## Replay and resource bounds

The canonical packet constants are defined in `core/udp_protocol.py`; protocol-v2 authentication serialization/persistence lives in `core/udp_auth_state.py`. Relevant bounds are:

- header size: 14 bytes
- authentication prefix size: 13 bytes
- authentication payload version: 2
- maximum datagram: 1450 bytes
- maximum chunks per frame: 1024
- maximum reconstructed frame: 2 MiB
- maximum in-flight frames per authenticated client/session: 8
- maximum authenticated clients retained by the runtime: 128
- persistent replay sessions: 4096 by default
- authentication frame ID: `0xFFFFFFFF`
- maximum video frame ID: `0xFFFFFFFE`

Incomplete frames expire quickly. The server watchdog is based on completed/decodeable video frames, not merely valid authentication or chunk traffic. This prevents a sender that only refreshes authentication or sends incomplete chunks from keeping a dead video stream falsely healthy.

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

Flash `esp32_cam_stream.ino` with the generated header and start the Raspberry Pi edge server from the same compatible source revision. After a protocol change, update/reflash both peers together.
