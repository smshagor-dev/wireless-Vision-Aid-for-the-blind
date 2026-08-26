import 'detection.dart';

class GuidanceEvent {
  const GuidanceEvent({
    required this.detection,
    required this.proximity,
    required this.direction,
    required this.urgent,
  });

  final Detection detection;
  final ProximityBand proximity;
  final SpatialDirection direction;
  final bool urgent;
}

class GuidanceEngine {
  GuidanceEngine({
    this.cooldown = const Duration(seconds: 6),
    this.batchInterval = const Duration(milliseconds: 1800),
  });

  final Duration cooldown;
  final Duration batchInterval;
  final Map<String, DateTime> _lastAnnouncements = {};
  DateTime? _lastBatchAt;

  GuidanceEvent? choose(List<Detection> detections, {DateTime? now}) {
    final events = chooseMany(detections, maxEvents: 1, now: now);
    return events.isEmpty ? null : events.first;
  }

  List<GuidanceEvent> chooseMany(
    List<Detection> detections, {
    int maxEvents = 3,
    DateTime? now,
  }) {
    if (maxEvents <= 0 || detections.isEmpty) return const [];
    final current = now ?? DateTime.now();
    final previousBatch = _lastBatchAt;
    if (previousBatch != null && current.difference(previousBatch) < batchInterval) {
      return const [];
    }

    final bestByLabel = <String, GuidanceEvent>{};
    for (final detection in detections) {
      if (detection.box.area <= 0) continue;
      final previous = _lastAnnouncements[detection.label];
      if (previous != null && current.difference(previous) < cooldown) continue;

      final proximity = classifyRelativeProximity(detection.box);
      final candidate = GuidanceEvent(
        detection: detection,
        proximity: proximity,
        direction: classifySpatialDirection(detection.box),
        urgent: proximity == ProximityBand.immediate,
      );
      final existing = bestByLabel[detection.label];
      if (existing == null || _compare(candidate, existing) < 0) {
        bestByLabel[detection.label] = candidate;
      }
    }

    final candidates = bestByLabel.values.toList(growable: false)..sort(_compare);
    if (candidates.isEmpty) return const [];

    final selected = candidates.take(maxEvents).toList(growable: false);
    _lastBatchAt = current;
    for (final event in selected) {
      _lastAnnouncements[event.detection.label] = current;
    }
    return selected;
  }

  int _compare(GuidanceEvent a, GuidanceEvent b) {
    final proximityCompare = _proximityRank(a.proximity).compareTo(_proximityRank(b.proximity));
    if (proximityCompare != 0) return proximityCompare;
    final confidenceCompare = b.detection.confidence.compareTo(a.detection.confidence);
    if (confidenceCompare != 0) return confidenceCompare;
    final areaCompare = b.detection.box.area.compareTo(a.detection.box.area);
    if (areaCompare != 0) return areaCompare;
    return a.detection.label.compareTo(b.detection.label);
  }

  void reset() {
    _lastAnnouncements.clear();
    _lastBatchAt = null;
  }

  int _proximityRank(ProximityBand band) => switch (band) {
        ProximityBand.immediate => 0,
        ProximityBand.close => 1,
        ProximityBand.medium => 2,
        ProximityBand.far => 3,
      };
}
