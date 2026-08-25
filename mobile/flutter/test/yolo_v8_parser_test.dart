import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/vision/detection.dart';
import 'package:wvab_mobile/core/vision/yolo_v8_parser.dart';

void main() {
  test('parses channels-first YOLOv8 output and applies NMS', () {
    const parser = YoloV8Parser(labels: ['person', 'car']);
    const candidates = 3;
    const features = 6;
    final values = List<double>.filled(features * candidates, 0);

    void setValue(int feature, int candidate, double value) {
      values[feature * candidates + candidate] = value;
    }

    // Two overlapping person detections; only the stronger one should survive.
    setValue(0, 0, 160); setValue(1, 0, 160); setValue(2, 0, 160); setValue(3, 0, 224);
    setValue(4, 0, 0.92); setValue(5, 0, 0.05);
    setValue(0, 1, 164); setValue(1, 1, 162); setValue(2, 1, 158); setValue(3, 1, 220);
    setValue(4, 1, 0.80); setValue(5, 1, 0.04);

    // Separate car.
    setValue(0, 2, 70); setValue(1, 2, 70); setValue(2, 2, 60); setValue(3, 2, 50);
    setValue(4, 2, 0.05); setValue(5, 2, 0.88);

    final detections = parser.parse(
      values: values,
      shape: const [1, features, candidates],
      inputSize: 320,
      confidenceThreshold: 0.5,
    );

    expect(detections, hasLength(2));
    expect(detections.first.label, 'person');
    expect(detections.first.confidence, closeTo(0.92, 0.0001));
    expect(detections.last.label, 'car');
    expect(classifyRelativeProximity(detections.first.box), ProximityBand.immediate);
  });

  test('supports candidates-first output layout', () {
    const parser = YoloV8Parser(labels: ['person']);
    final detections = parser.parse(
      values: const [160, 160, 80, 100, 0.9],
      shape: const [1, 1, 5],
      inputSize: 320,
      confidenceThreshold: 0.5,
    );
    expect(detections.single.label, 'person');
    expect(detections.single.box.height, closeTo(100 / 320, 0.0001));
  });

  test('rejects malformed output instead of guessing', () {
    const parser = YoloV8Parser(labels: ['person']);
    expect(
      () => parser.parse(
        values: const [1, 2, 3],
        shape: const [1, 5, 2],
        inputSize: 320,
        confidenceThreshold: 0.5,
      ),
      throwsFormatException,
    );
  });
}
