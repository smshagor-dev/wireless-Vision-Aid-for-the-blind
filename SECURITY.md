# Security Policy

WVAB processes live camera data, network traffic, device credentials, replay-security state, and assistive guidance. Security reports are treated seriously, but the project remains a research/assistive prototype and is **not** a certified medical or mobility-safety device.

## Supported code

Security fixes are developed against the current `main` branch and active hardening branches. Older source snapshots, forks, prebuilt binaries, models, generated credentials, and third-party dependencies may not receive backported fixes.

Before reporting a vulnerability, reproduce it against the current source revision when practical and record the exact commit SHA, platform, Python/ESP32 versions, secure-UDP protocol version, and configuration used.

## Reporting a vulnerability

Do **not** publish exploitable security details, live device credentials, AES keys, UDP/WebSocket tokens, private camera URLs, replay-state contents from a live deployment, or personal video data in a public issue.

Prefer GitHub's private vulnerability-reporting / Security Advisory flow when it is available for this repository. If that flow is not available, contact the repository maintainer privately through the GitHub account associated with this repository before public disclosure.

A useful report includes:

- affected commit/tag and runtime path
- deployment topology (Python sender, ESP32-CAM, Raspberry Pi, Docker, etc.)
- minimal reproduction steps or proof of concept
- expected vs. observed behavior
- security impact and realistic attacker position
- relevant logs with secrets and personal data removed
- whether the replay-state file/volume was preserved, lost, corrupted, or restored
- suggested mitigation, if known

Please do not test against devices or networks you do not own or have explicit permission to assess.

## Security-sensitive areas

Reports are especially useful for:

- AES-GCM nonce/session handling, protocol-v2 auth counters, restart replay protection, frame replay/order handling, packet parsing, or resource exhaustion
- persistent replay-state rollback, corruption, unsafe replacement, permission errors, or bypasses
- WebSocket control authentication or unintended remote exposure
- generated ESP32/Raspberry Pi credential handling and rotation
- unsafe fallback paths that bypass encrypted/authenticated transport
- camera URL credential leakage or unintended network discovery
- path traversal, unsafe file writes, command injection, or privilege escalation in launch/deployment tooling
- dependency/model/font supply-chain integrity or release provenance
- logic that incorrectly promotes uncertain navigation state to `GUIDANCE_AVAILABLE`

## Credential and replay-state handling

`esp32_secrets.h`, `deployment/rpi/wvab_edge.env`, `.env*`, local camera credentials, and equivalent generated secrets must remain private and untracked.

`state/udp_replay_state.json` (or the configured equivalent) is not a credential file: it stores session IDs, auth counters, and next-frame baselines, not the AES key/token. It is nevertheless part of the security boundary and must be preserved against accidental deletion/rollback. Docker stores the same state in the `wvab-replay-state` volume.

If credentials may have been exposed **or persistent replay state is lost/rolled back**:

1. Stop the affected deployment.
2. Rotate the matched ESP32/Raspberry Pi pair with `python tools/generate_device_secrets.py --force ...`.
3. Reflash the ESP32 with the new generated header.
4. Remove the obsolete replay-state file/volume only as part of this credential rotation.
5. Restart the server with the new environment file and fresh replay state.
6. Remove exposed material from logs, artifacts, caches, and release assets where possible.

A corrupt replay-state file intentionally fails server startup rather than silently resetting anti-replay history. Do not bypass that failure by deleting the file and continuing with the same field credentials.

Do not restore an old retired UDP sender session as a workaround for replay protection.

## UDP protocol compatibility

Current secure UDP authentication is protocol v2. Its encrypted authentication plaintext contains a version byte, monotonic uint64 authentication counter, next uint32 frame ID, and deployment token. The server persists the highest accepted counter before granting/renewing a session and uses the next-frame value to establish a replay baseline across normal restarts.

Legacy token-only authentication is deliberately rejected. ESP32/Python senders and the server must be updated from compatible source revisions after a secure-UDP protocol change.

## Dependency and model security

WVAB depends on third-party Python packages, ESP32 tooling, models, and font assets. They retain their own security and licensing responsibilities. Review `THIRD_PARTY_NOTICES.md` and the exact resolved dependencies used for a release.

The optional MiDaS provisioner verifies its expected downloaded weight checksum. New downloadable model assets should use the same explicit-source and integrity-verification pattern rather than silent runtime downloads.

## Safety-related security boundary

A security fix does not make WVAB field-safe. The navigation pipeline deliberately fails toward `STOP` or `DEGRADED` when required geometry/localization inputs are unavailable or untrusted. Do not weaken those gates to keep a demo running.

Hardware soak testing, representative hazard validation, latency/error measurements, battery/thermal tests, and blind/low-vision user evaluation remain separate release-evidence requirements documented in `PRODUCTION_READINESS.md`.

## Disclosure

Once a report is understood and a fix is available, disclose enough information for users to identify affected revisions and update safely without exposing active secrets or unnecessary personal data.
