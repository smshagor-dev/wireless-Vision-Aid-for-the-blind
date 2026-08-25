import 'coco_labels.dart';
import 'detection.dart';

class YoloV8Parser {
  const YoloV8Parser({this.labels = coco80Labels, this.iouThreshold = 0.45});

  final List<String> labels;
  final double iouThreshold;

  List<Detection> parse({
    required List<num> values,
    required List<int> shape,
    required int inputSize,
    required double confidenceThreshold,
  }) {
    if (shape.length != 3 || shape.first != 1) {
      throw FormatException('Unexpected YOLO output shape: $shape');
    }
    final channelsFirst = shape[1] >= 5 && shape[1] <= 256;
    final featureCount = channelsFirst ? shape[1] : shape[2];
    final candidateCount = channelsFirst ? shape[2] : shape[1];
    if (featureCount < 5 || featureCount - 4 > labels.length) {
      throw FormatException('Unsupported YOLO feature count: $featureCount');
    }
    if (values.length != featureCount * candidateCount) {
      throw FormatException('YOLO output length does not match shape.');
    }

    double at(int candidate, int feature) {
      final index = channelsFirst
          ? feature * candidateCount + candidate
          : candidate * featureCount + feature;
      return values[index].toDouble();
    }

    final raw = <Detection>[];
    for (var candidate = 0; candidate < candidateCount; candidate++) {
      var bestClass = -1;
      var bestScore = 0.0;
      for (var classIndex = 0; classIndex < featureCount - 4; classIndex++) {
        final score = at(candidate, classIndex + 4);
        if (score > bestScore) {
          bestScore = score;
          bestClass = classIndex;
        }
      }
      if (bestClass < 0 || bestScore < confidenceThreshold) continue;

      final cx = at(candidate, 0);
      final cy = at(candidate, 1);
      final width = at(candidate, 2).clamp(0.0, inputSize.toDouble());
      final height = at(candidate, 3).clamp(0.0, inputSize.toDouble());
      final halfW = width / 2;
      final halfH = height / 2;
      final box = BoundingBox(
        left: (cx - halfW) / inputSize,
        top: (cy - halfH) / inputSize,
        right: (cx + halfW) / inputSize,
        bottom: (cy + halfH) / inputSize,
      ).clamp();
      if (box.width <= 0 || box.height <= 0) continue;
      raw.add(Detection(
        classId: bestClass,
        label: labels[bestClass],
        confidence: bestScore,
        box: box,
      ));
    }

    raw.sort((a, b) => b.confidence.compareTo(a.confidence));
    final kept = <Detection>[];
    for (final candidate in raw) {
      final overlaps = kept.any(
        (existing) => existing.classId == candidate.classId && _iou(existing.box, candidate.box) > iouThreshold,
      );
      if (!overlaps) kept.add(candidate);
    }
    return kept;
  }

  double _iou(BoundingBox a, BoundingBox b) {
    final left = a.left > b.left ? a.left : b.left;
    final top = a.top > b.top ? a.top : b.top;
    final right = a.right < b.right ? a.right : b.right;
    final bottom = a.bottom < b.bottom ? a.bottom : b.bottom;
    final width = (right - left).clamp(0.0, 1.0);
    final height = (bottom - top).clamp(0.0, 1.0);
    final intersection = width * height;
    final union = a.area + b.area - intersection;
    return union <= 0 ? 0 : intersection / union;
  }
}
