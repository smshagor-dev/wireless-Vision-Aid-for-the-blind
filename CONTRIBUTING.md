# Contributing

## Local setup

WVAB requires Python 3.10+.

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For lightweight unit/CI work only:

```bash
python -m pip install -r requirements-ci.txt
```

## Test before a PR

Run device-independent validation:

```bash
python -m pytest -q
python -m compileall -q .
python test_system.py
python udp_streaming.py --help
```

If the change affects hardware/runtime behavior, also run the relevant opt-in diagnostics on a suitable host and record the result. Do not report hardware, safety, latency, or field-readiness evidence that was not actually measured.

## Coding guidelines

- Keep changes reviewable and preserve supported runtime behavior unless the change is intentional and documented.
- Keep `udp_streaming.py` as the compatibility entrypoint; transport/session implementation lives in `core/udp_runtime.py` and wire constants live in `core/udp_protocol.py`.
- Keep the Python sender/server and `esp32_cam_stream.ino` on the same documented secure UDP wire contract.
- Treat bounding-box/MiDaS monocular proximity as non-metric unless explicit calibration requirements are satisfied.
- Keep device credentials, generated datasets/models, build output, caches, and runtime logs out of Git.
- Never add shared example production secrets or disable authentication/encryption in supported deployment paths.
- Update tests and documentation whenever config, protocol, deployment, or CLI behavior changes.

## Pull request checklist

- [ ] Core tests pass on supported Python versions or the runner limitation is documented.
- [ ] Python source compiles and lightweight CLIs parse successfully.
- [ ] Secure UDP protocol changes include Python + ESP32 + protocol-doc + test updates together.
- [ ] Package/wheel content remains complete.
- [ ] No secrets/generated artifacts are tracked.
- [ ] Config/deployment changes are documented.
- [ ] Hardware-dependent claims include real validation evidence rather than assumptions.
