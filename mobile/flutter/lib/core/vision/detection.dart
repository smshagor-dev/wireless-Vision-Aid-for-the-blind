class BoundingBox {
  const BoundingBox({required this.left, required this.top, required this.right, required this.bottom});

  final double left;
  final double top;
  final double right;
  final double bottom;

  double get width => (right - left).clamp(0.0, 1.0);
  double get height => (bottom - top).clamp(0.0, 1.0);
  double get area => width * height;
  double get centerX => ((left + right) / 2).clamp(0.0, 1.0);

  BoundingBox clamp() => BoundingBox(
        left: left.clamp(0.0, 1.0),
        top: top.clamp(0.0, 1.0),
        right: right.clamp(0.0, 1.0),
        bottom: bottom.clamp(0.0, 1.0),
      );
}

class Detection {
  const Detection({
    required this.classId,
    required this.label,
    required this.confidence,
    required this.box,
  });

  final int classId;
  final String label;
  final double confidence;
  final BoundingBox box;
}

enum ProximityBand { immediate, close, medium, far }
enum SpatialDirection { left, center, right }

ProximityBand classifyRelativeProximity(BoundingBox box) {
  final ratio = box.height;
  if (ratio > 0.60) return ProximityBand.immediate;
  if (ratio > 0.40) return ProximityBand.close;
  if (ratio > 0.20) return ProximityBand.medium;
  return ProximityBand.far;
}

SpatialDirection classifySpatialDirection(BoundingBox box) {
  final center = box.centerX;
  if (center < 0.38) return SpatialDirection.left;
  if (center > 0.62) return SpatialDirection.right;
  return SpatialDirection.center;
}
