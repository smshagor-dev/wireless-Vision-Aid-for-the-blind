# Security Policy

WVAB processes live camera data, network traffic, device credentials, and assistive guidance. Security reports are treated seriously, but the project remains a research/assistive prototype and is **not** a certified medical or mobility-safety device.

## Supported code

Security fixes are developed against the current `main` branch and active hardening branches. Older source snapshots, forks, prebuilt binaries, models, generated credentials, and third-party dependencies may not receive backported fixes.

Before reporting a vulnerability, reproduce it against the current source revision when practical and record the exact commit SHA, platform, Python/ESP32 versions, and configuration used.

## Reporting a vulnerability

Do **not** publish exploitable security details, live device credentials, AES keys, UDP/WebSocket tokens, private camera URLs, or personal video data in a public issue.

Prefer GitHub's private vulnerability-reporting / Security Advisory flow when it is available for this repository. If that flow is not available, contact the repository maintainer privately through the GitHub account associated with this repository before public disclosure.

A useful report includes:

- affected commit/tag and runtime path
- deployment topology (Python sender, ESP32-CAM, Raspberry Pi, Docker, etc.)
- minimal reproduction steps or proof of concept
- expected vs. observed behavior
- security impact and realistic attacker position
- relevant logs with secrets and personal data removed
- suggested mitigation, if known

Please do not test against devices or networks you do not own or have explicit permission to assess.

## Security-sensitive areas

Reports are especially useful for:

- AES-GCM nonce/session handling, authentication, replay protection, packet parsing, or resource exhaustion
- WebSocket control authentication or unintended remote exposure
- generated ESP32/Raspberry Pi credential handling and rotation
- unsafe fallback paths that bypass encrypted/authenticated transport
- camera URL credential leakage or unintended network discovery
- path traversal, unsafe file writes, command injection, or privilege escalation in launch/deployment tooling
- dependency/model/font supply-chain integrity or release provenance
- logic that incorrectly promotes uncertain navigation state to `GUIDANCE_AVAILABLE`

## Credential handling

`esp32_secrets.h`, `deployment/rpi/wvab_edge.env`, `.env*`, local camera credentials, and equivalent generated secrets must remain private and untracked.

If credentials may have been exposed:

1. Stop the affected deployment.
2. Rotate the matched ESP32/Raspberry Pi pair with `python tools/generate_device_secrets.py --force ...`.
3. Reflash the ESP32 with the new generated header.
4. Restart the server with the new environment file.
5. Remove exposed material from logs, artifacts, caches, and release assets where possible.

Do not restore an old retired UDP sender session as a workaround for replay protection.

## Dependency and model security

WVAB depends on third-party Python packages, ESP32 tooling, models, and font assets. They retain their own security and licensing responsibilities. Review `THIRD_PARTY_NOTICES.md` and the exact resolved dependencies used for a release.

The optional MiDaS provisioner verifies its expected downloaded weight checksum. New downloadable model assets should use the same explicit-source and integrity-verification pattern rather than silent runtime downloads.

## Safety-related security boundary

A security fix does not make WVAB field-safe. The navigation pipeline deliberately fails toward `STOP` or `DEGRADED` when required geometry/localization inputs are unavailable or untrusted. Do not weaken those gates to keep a demo running.

Hardware soak testing, representative hazard validation, latency/error measurements, battery/thermal tests, and blind/low-vision user evaluation remain separate release-evidence requirements documented in `PRODUCTION_READINESS.md`.

## Disclosure

Once a report is understood and a fix is available, disclose enough information for users to identify affected revisions and update safely without exposing active secrets or unnecessary personal data.
