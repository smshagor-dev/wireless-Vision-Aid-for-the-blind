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
enum NavigationCue { moveLeft, moveRight, forward, stop }

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

/// Conservative monocular estimate used only when the detected class has a
/// reasonably stable real-world vertical size. This is intentionally
/// approximate: a single RGB frame cannot provide certified metric depth.
double? estimateApproximateDistanceMeters(Detection detection) {
  const referenceHeightMeters = <String, double>{
    'person': 1.70,
    'bicycle': 1.05,
    'car': 1.50,
    'motorcycle': 1.10,
    'bus': 3.10,
    'train': 3.40,
    'truck': 3.00,
    'traffic light': 0.75,
    'stop sign': 0.75,
    'parking meter': 1.20,
    'bench': 0.80,
    'chair': 0.90,
    'couch': 0.85,
    'toilet': 0.75,
    'refrigerator': 1.75,
  };
  final objectHeight = referenceHeightMeters[detection.label];
  final normalizedPixelHeight = detection.box.height;
  if (objectHeight == null || normalizedPixelHeight < 0.08) return null;

  // Approximate vertical focal length for a typical ~60 degree phone-camera
  // field of view, expressed in normalized frame-height units.
  const normalizedFocalLength = 0.87;
  final meters = (objectHeight * normalizedFocalLength) / normalizedPixelHeight;
  if (!meters.isFinite || meters <= 0 || meters > 20) return null;
  return meters.clamp(0.4, 20.0);
}
