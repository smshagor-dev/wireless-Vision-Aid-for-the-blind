import 'detection.dart';

class GuidanceEvent {
  const GuidanceEvent({
    required this.detection,
    required this.proximity,
    required this.direction,
    required this.navigationCue,
    required this.urgent,
    this.approximateDistanceMeters,
  });

  final Detection detection;
  final ProximityBand proximity;
  final SpatialDirection direction;
  final NavigationCue navigationCue;
  final bool urgent;
  final double? approximateDistanceMeters;
}

class GuidanceEngine {
  GuidanceEngine({
    this.cooldown = const Duration(seconds: 4),
    this.focusHold = const Duration(seconds: 2),
  });

  final Duration cooldown;
  final Duration focusHold;
  final Map<String, DateTime> _lastAnnouncements = <String, DateTime>{};
  String? _focusedLabel;
  SpatialDirection? _focusedDirection;
  DateTime? _focusLastSeen;

  GuidanceEvent? choose(List<Detection> detections, {DateTime? now}) {
    if (detections.isEmpty) {
      resetFocus();
      return null;
    }
    final current = now ?? DateTime.now();
    final candidates = detections.where((item) => item.box.area > 0).toList(growable: false);
    if (candidates.isEmpty) return null;

    final focused = _findHeldFocus(candidates, current) ?? _selectPrimary(candidates);
    final proximity = classifyRelativeProximity(focused.box);
    final direction = classifySpatialDirection(focused.box);
    final cue = _navigationCue(focused, candidates, proximity, direction);
    final key = '${focused.label}:${proximity.name}:${direction.name}:${cue.name}';
    final last = _lastAnnouncements[key];

    _focusedLabel = focused.label;
    _focusedDirection = direction;
    _focusLastSeen = current;

    if (last != null && current.difference(last) < cooldown) return null;
    _lastAnnouncements[key] = current;

    return GuidanceEvent(
      detection: focused,
      proximity: proximity,
      direction: direction,
      navigationCue: cue,
      urgent: proximity == ProximityBand.immediate || cue == NavigationCue.stop,
      approximateDistanceMeters: estimateApproximateDistanceMeters(focused),
    );
  }

  Detection? _findHeldFocus(List<Detection> detections, DateTime current) {
    final label = _focusedLabel;
    final lastSeen = _focusLastSeen;
    if (label == null || lastSeen == null || current.difference(lastSeen) > focusHold) return null;

    final matches = detections.where((item) => item.label == label).toList(growable: false);
    if (matches.isEmpty) return null;
    matches.sort((a, b) {
      final aDirection = classifySpatialDirection(a.box) == _focusedDirection ? 0 : 1;
      final bDirection = classifySpatialDirection(b.box) == _focusedDirection ? 0 : 1;
      final directionCompare = aDirection.compareTo(bDirection);
      if (directionCompare != 0) return directionCompare;
      return _compareRisk(a, b);
    });
    return matches.first;
  }

  Detection _selectPrimary(List<Detection> detections) {
    final ordered = List<Detection>.from(detections)..sort(_compareRisk);
    return ordered.first;
  }

  int _compareRisk(Detection a, Detection b) {
    final proximityCompare = _proximityRank(classifyRelativeProximity(a.box))
        .compareTo(_proximityRank(classifyRelativeProximity(b.box)));
    if (proximityCompare != 0) return proximityCompare;

    // Objects in the walking corridor are more relevant than equally-close
    // detections at the far edges of the frame.
    final centerCompare = _centerRank(a.box).compareTo(_centerRank(b.box));
    if (centerCompare != 0) return centerCompare;

    final areaCompare = b.box.area.compareTo(a.box.area);
    if (areaCompare != 0) return areaCompare;
    final confidenceCompare = b.confidence.compareTo(a.confidence);
    if (confidenceCompare != 0) return confidenceCompare;
    return a.label.compareTo(b.label);
  }

  NavigationCue _navigationCue(
    Detection focused,
    List<Detection> detections,
    ProximityBand proximity,
    SpatialDirection direction,
  ) {
    if (proximity == ProximityBand.far) return NavigationCue.forward;

    final left = _laneOccupancy(detections, 0.00, 0.38);
    final center = _laneOccupancy(detections, 0.31, 0.69);
    final right = _laneOccupancy(detections, 0.62, 1.00);

    final blockedThreshold = proximity == ProximityBand.immediate ? 0.42 : 0.62;
    final leftBlocked = left >= blockedThreshold;
    final rightBlocked = right >= blockedThreshold;
    final centerBlocked = center >= blockedThreshold;

    if ((proximity == ProximityBand.immediate && leftBlocked && rightBlocked) ||
        (centerBlocked && leftBlocked && rightBlocked)) {
      return NavigationCue.stop;
    }

    if (direction == SpatialDirection.left && !rightBlocked) return NavigationCue.moveRight;
    if (direction == SpatialDirection.right && !leftBlocked) return NavigationCue.moveLeft;

    if (direction == SpatialDirection.center || centerBlocked) {
      if (!leftBlocked && !rightBlocked) {
        return left <= right ? NavigationCue.moveLeft : NavigationCue.moveRight;
      }
      if (!leftBlocked) return NavigationCue.moveLeft;
      if (!rightBlocked) return NavigationCue.moveRight;
      return NavigationCue.stop;
    }

    return NavigationCue.forward;
  }

  double _laneOccupancy(List<Detection> detections, double laneLeft, double laneRight) {
    var score = 0.0;
    final laneWidth = laneRight - laneLeft;
    for (final detection in detections) {
      final overlapLeft = detection.box.left > laneLeft ? detection.box.left : laneLeft;
      final overlapRight = detection.box.right < laneRight ? detection.box.right : laneRight;
      final overlap = (overlapRight - overlapLeft).clamp(0.0, laneWidth);
      if (overlap <= 0) continue;
      final proximityWeight = switch (classifyRelativeProximity(detection.box)) {
        ProximityBand.immediate => 1.0,
        ProximityBand.close => 0.72,
        ProximityBand.medium => 0.38,
        ProximityBand.far => 0.10,
      };
      score += (overlap / laneWidth) * detection.box.height * proximityWeight;
    }
    return score;
  }

  int _centerRank(BoundingBox box) {
    final distance = (box.centerX - 0.5).abs();
    if (distance < 0.18) return 0;
    if (distance < 0.34) return 1;
    return 2;
  }

  void resetFocus() {
    _focusedLabel = null;
    _focusedDirection = null;
    _focusLastSeen = null;
  }

  void reset() {
    _lastAnnouncements.clear();
    resetFocus();
  }

  int _proximityRank(ProximityBand band) => switch (band) {
        ProximityBand.immediate => 0,
        ProximityBand.close => 1,
        ProximityBand.medium => 2,
        ProximityBand.far => 3,
      };
}
