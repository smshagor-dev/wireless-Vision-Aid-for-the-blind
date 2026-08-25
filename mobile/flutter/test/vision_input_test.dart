import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/vision/detection.dart';
import 'package:wvab_mobile/core/vision/vision_input.dart';

void main() {
  test('letterbox transform restores source-space box coordinates', () {
    const transform = LetterboxTransform(
      inputSize: 320,
      sourceWidth: 640,
      sourceHeight: 480,
      scale: 0.5,
      padX: 0,
      padY: 40,
    );

    final restored = transform.modelBoxToSource(
      const BoundingBox(
        left: 0.25,
        top: 0.3125,
        right: 0.75,
        bottom: 0.6875,
      ),
    );

    expect(restored.left, closeTo(0.25, 1e-9));
    expect(restored.top, closeTo(0.25, 1e-9));
    expect(restored.right, closeTo(0.75, 1e-9));
    expect(restored.bottom, closeTo(0.75, 1e-9));
  });

  test('letterbox transform clamps boxes that overlap padding', () {
    const transform = LetterboxTransform(
      inputSize: 320,
      sourceWidth: 640,
      sourceHeight: 480,
      scale: 0.5,
      padX: 0,
      padY: 40,
    );

    final restored = transform.modelBoxToSource(
      const BoundingBox(left: 0, top: 0, right: 1, bottom: 1),
    );

    expect(restored.left, 0);
    expect(restored.top, 0);
    expect(restored.right, 1);
    expect(restored.bottom, 1);
  });
}
