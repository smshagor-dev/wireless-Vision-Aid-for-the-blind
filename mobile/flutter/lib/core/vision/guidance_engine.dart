import 'detection.dart';

class GuidanceEvent {
  const GuidanceEvent({required this.detection, required this.proximity, required this.urgent});

  final Detection detection;
  final ProximityBand proximity;
  final bool urgent;
}

class GuidanceEngine {
  GuidanceEngine({this.cooldown = const Duration(milliseconds: 2500)});

  final Duration cooldown;
  final Map<String, DateTime> _lastAnnouncements = {};

  static const _priority = <String, int>{
    'person': 1,
    'car': 1,
    'truck': 1,
    'bus': 1,
    'bicycle': 2,
    'motorcycle': 2,
    'traffic light': 3,
    'stop sign': 3,
    'chair': 4,
    'bench': 4,
    'potted plant': 4,
  };

  GuidanceEvent? choose(List<Detection> detections, {DateTime? now}) {
    final current = now ?? DateTime.now();
    final candidates = <GuidanceEvent>[];
    for (final detection in detections) {
      if (!_priority.containsKey(detection.label)) continue;
      final proximity = classifyRelativeProximity(detection.box);
      final key = '${detection.label}:${proximity.name}';
      final previous = _lastAnnouncements[key];
      if (previous != null && current.difference(previous) < cooldown) continue;
      candidates.add(GuidanceEvent(
        detection: detection,
        proximity: proximity,
        urgent: proximity == ProximityBand.immediate,
      ));
    }
    if (candidates.isEmpty) return null;
    candidates.sort((a, b) {
      final proximityCompare = _proximityRank(a.proximity).compareTo(_proximityRank(b.proximity));
      if (proximityCompare != 0) return proximityCompare;
      final priorityCompare = (_priority[a.detection.label] ?? 99).compareTo(_priority[b.detection.label] ?? 99);
      if (priorityCompare != 0) return priorityCompare;
      return b.detection.confidence.compareTo(a.detection.confidence);
    });
    final selected = candidates.first;
    _lastAnnouncements['${selected.detection.label}:${selected.proximity.name}'] = current;
    return selected;
  }

  void reset() => _lastAnnouncements.clear();

  int _proximityRank(ProximityBand band) => switch (band) {
        ProximityBand.immediate => 0,
        ProximityBand.close => 1,
        ProximityBand.medium => 2,
        ProximityBand.far => 3,
      };
}
