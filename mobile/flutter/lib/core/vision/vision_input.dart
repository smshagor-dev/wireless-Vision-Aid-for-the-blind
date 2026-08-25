import 'dart:typed_data';

import 'detection.dart';

class LetterboxTransform {
  const LetterboxTransform({
    required this.inputSize,
    required this.sourceWidth,
    required this.sourceHeight,
    required this.scale,
    required this.padX,
    required this.padY,
  });

  final int inputSize;
  final int sourceWidth;
  final int sourceHeight;
  final double scale;
  final double padX;
  final double padY;

  BoundingBox modelBoxToSource(BoundingBox box) {
    if (sourceWidth <= 0 || sourceHeight <= 0 || scale <= 0) {
      throw StateError('Invalid WVAB letterbox transform.');
    }
    double unmapX(double normalized) => ((normalized * inputSize) - padX) / scale / sourceWidth;
    double unmapY(double normalized) => ((normalized * inputSize) - padY) / scale / sourceHeight;

    return BoundingBox(
      left: unmapX(box.left),
      top: unmapY(box.top),
      right: unmapX(box.right),
      bottom: unmapY(box.bottom),
    ).clamp();
  }
}

class PreparedVisionInput {
  const PreparedVisionInput({required this.tensor, required this.transform});

  final Float32List tensor;
  final LetterboxTransform transform;
}
