import '../vision/detection.dart';

class DetectionHistoryEntry {
  const DetectionHistoryEntry({
    required this.id,
    required this.timestamp,
    required this.classId,
    required this.label,
    required this.confidence,
    required this.proximity,
    required this.direction,
    required this.cameraSource,
  });

  final String id;
  final DateTime timestamp;
  final int classId;
  final String label;
  final double confidence;
  final ProximityBand proximity;
  final SpatialDirection direction;
  final String cameraSource;

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toUtc().toIso8601String(),
        'classId': classId,
        'label': label,
        'confidence': confidence,
        'proximity': proximity.name,
        'direction': direction.name,
        'cameraSource': cameraSource,
      };

  static DetectionHistoryEntry? fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final timestamp = DateTime.tryParse(json['timestamp']?.toString() ?? '');
    final label = json['label'];
    final confidence = json['confidence'];
    if (id is! String || timestamp == null || label is! String || confidence is! num) return null;

    return DetectionHistoryEntry(
      id: id,
      timestamp: timestamp.toLocal(),
      classId: (json['classId'] as num?)?.toInt() ?? -1,
      label: label,
      confidence: confidence.toDouble(),
      proximity: _proximityFromName(json['proximity']?.toString()),
      direction: _directionFromName(json['direction']?.toString()),
      cameraSource: json['cameraSource']?.toString() ?? 'phone',
    );
  }

  static ProximityBand _proximityFromName(String? value) {
    for (final item in ProximityBand.values) {
      if (item.name == value) return item;
    }
    return ProximityBand.far;
  }

  static SpatialDirection _directionFromName(String? value) {
    for (final item in SpatialDirection.values) {
      if (item.name == value) return item;
    }
    return SpatialDirection.center;
  }
}
