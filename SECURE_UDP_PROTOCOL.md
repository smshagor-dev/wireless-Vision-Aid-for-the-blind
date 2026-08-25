# WVAB Secure UDP Protocol

This document describes the transport used by `udp_streaming.py` and `esp32_cam_stream.ino` on the same source revision. The two peers must be deployed from compatible revisions; older packet formats are intentionally not accepted after the replay/header-integrity hardening.

## Security scope

The supported deployment path uses:

- AES-GCM with a deployment-specific 16, 24, or 32-byte key
- a deployment-specific authentication token of at least 16 characters
- a fresh 96-bit random base nonce for every authentication packet and every video frame
- the complete packet header as AES-GCM Additional Authenticated Data (AAD)
- authentication nonce replay rejection during the server process lifetime
- monotonically ordered 32-bit frame serials with wrap-aware replay rejection
- bounded chunks, frame bytes, and per-client in-flight frame buffers

The transport provides confidentiality and integrity on the local UDP link. It is not a substitute for secure device provisioning, key rotation, physical security, or a VPN when traffic crosses an untrusted routed network.

## Header

Every datagram starts with a 10-byte network-byte-order header:

| Field | Size | Description |
| --- | ---: | --- |
| `frame_id` | 4 bytes | Video frame serial. `0xFFFFFFFF` is reserved for authentication. |
| `total_chunks` | 2 bytes | Number of chunks in the video frame; zero for authentication. |
| `chunk_index` | 2 bytes | Zero-based chunk index; zero for authentication. |
| `payload_size` | 2 bytes | Bytes after the header in this datagram. |

For every encrypted datagram, these exact 10 header bytes are passed to AES-GCM as AAD. Changing a frame ID, chunk count, chunk index, or payload size therefore invalidates the GCM tag.

## Encrypted authentication datagram

Authentication uses:

```text
header(frame_id=0xFFFFFFFF, total_chunks=0, chunk_index=0)
base_nonce[12]
tag[16]
ciphertext[token_length]
```

The server validates the GCM tag and token using constant-time secret comparison, remembers the authentication nonce for the authentication TTL, and rejects a repeated nonce during that interval.

Authentication establishes permission for the sender UDP source address/port for a bounded TTL. Python and ESP32 senders refresh authentication while actively streaming.

## Encrypted video datagram

Each chunk uses:

```text
header(frame_id, total_chunks, chunk_index)
base_nonce[12]
tag[16]
ciphertext[chunk_plaintext_length]
```

Every chunk carries the same frame base nonce. The actual GCM nonce is derived by adding `chunk_index` to the final 32 bits of that base nonce. Because every chunk includes the base nonce, datagram reordering does not require chunk zero to arrive first.

The receiver requires all chunks for a frame to use the same base nonce and authenticates each chunk independently before buffering plaintext.

## Replay and resource bounds

The current protocol constants are defined in `core/udp_protocol.py` and mirrored in the ESP32 firmware where applicable:

- maximum datagram: 1450 bytes
- maximum chunks per frame: 1024
- maximum reconstructed frame: 2 MiB
- maximum in-flight frames per authenticated client: 8
- authentication frame ID: `0xFFFFFFFF`
- maximum video frame ID: `0xFFFFFFFE`

After a frame is completed, an equal or older frame serial from that authenticated sender is rejected. Serial comparison is wrap-aware so `0` is newer than `0xFFFFFFFE` after a valid wrap.

Incomplete frames expire quickly and are evicted when a client exceeds its in-flight limit.

## Development exceptions

Unencrypted UDP is disabled unless `WVAB_ALLOW_INSECURE_UDP=1` is set explicitly. That switch is only for isolated development and must not be used for a wearable/field deployment.

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
