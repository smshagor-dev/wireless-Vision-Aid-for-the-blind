# Third-Party Notices

WVAB contains original project code plus third-party software, model assets, and font assets. The repository-level MIT `LICENSE` should not be read as relicensing third-party components. Each third-party component remains subject to its own applicable license and terms.

This file is an engineering notice, not legal advice. Verify the licenses that apply to the exact versions and deployment model before distribution or commercial use.

## Ultralytics YOLO

WVAB currently uses the `ultralytics` Python package and a YOLOv8 model path for object detection/training/export.

Ultralytics' current official licensing pages state that its open-source YOLO software and trained models are provided under **AGPL-3.0 by default**, with separate commercial/Enterprise licensing available for proprietary and commercial use.

Upstream references:

- https://www.ultralytics.com/license
- https://www.ultralytics.com/legal/agpl-3-0-software-license
- https://www.ultralytics.com/legal/terms-of-service

Before using WVAB in a proprietary, commercial, embedded, or otherwise non-AGPL deployment, review the current Ultralytics terms and obtain any license required for that use case. Do not assume WVAB's MIT license overrides Ultralytics software/model terms.

The repository currently retains `yolov8n.pt` for its offline baseline. That file must be treated as a third-party model asset rather than original MIT-licensed WVAB code.

## MiDaS

WVAB can optionally provision the MiDaS v2.1 small depth model and cached upstream source for monocular relative-depth experiments.

The upstream MiDaS repository identifies its code as MIT licensed. The upstream repository was archived in 2025, so WVAB pins the expected legacy weight URL/checksum and treats the integration as optional.

Upstream reference:

- https://github.com/isl-org/MiDaS

Dataset/model provenance and any additional terms associated with upstream training data remain separate from WVAB's own source license.

## Noto fonts

WVAB bundles Noto font files for Bengali, Devanagari, and Arabic overlays. Noto font software is distributed by Google under the **SIL Open Font License 1.1 (OFL-1.1)**.

Upstream references:

- https://github.com/notofonts
- https://openfontlicense.org/

The bundled font files retain their upstream font license; they are not relicensed under WVAB's MIT license.

## Python/system dependencies

Packages listed in `requirements.txt`, `requirements-accelerators.txt`, and transitive dependencies retain their own upstream licenses. A release intended for redistribution should generate and review a dependency Software Bill of Materials (SBOM) / license inventory for the resolved environment rather than relying only on this human-maintained summary.

## Release checklist

Before a public production/commercial release:

1. Review the exact resolved dependency/model/font license inventory.
2. Confirm the intended use satisfies Ultralytics' current licensing terms or obtain the appropriate commercial license.
3. Preserve required third-party notices/licenses with redistributed assets.
4. Generate an SBOM for the actual release environment/artifacts.
5. Record the model identity/checksum and source revision in release documentation.
