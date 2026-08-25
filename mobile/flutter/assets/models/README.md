# WVAB Mobile Models

The Android build generates `yolov8n_320.onnx` from the repository's pinned local `yolov8n.pt` during the mobile model-export gate. The generated ONNX file is intentionally not treated as hand-authored source.

Runtime code loads the model only from the packaged Flutter asset path:

`assets/models/yolov8n_320.onnx`

The application must fail closed for detection when that validated asset cannot be loaded; it must not silently download a model or fall back to a remote backend.
