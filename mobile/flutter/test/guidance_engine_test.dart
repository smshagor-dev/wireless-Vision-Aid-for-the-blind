import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/vision/detection.dart';
import 'package:wvab_mobile/core/vision/guidance_engine.dart';

void main() {
  Detection detection(String label, double height, double confidence, {double left = 0.2, double right = 0.8}) => Detection(
        classId: 0,
        label: label,
        confidence: confidence,
        box: BoundingBox(left: left, top: 0.1, right: right, bottom: 0.1 + height),
      );

  test('immediate hazards outrank farther hazards without class bias', () {
    final engine = GuidanceEngine(batchInterval: Duration.zero);
    final event = engine.choose([
      detection('car', 0.25, 0.95),
      detection('book', 0.70, 0.80),
    ], now: DateTime.utc(2026, 1, 1));
    expect(event, isNotNull);
    expect(event!.detection.label, 'book');
    expect(event.proximity, ProximityBand.immediate);
    expect(event.urgent, isTrue);
  });

  test('cooldown suppresses repeated label announcements', () {
    final engine = GuidanceEngine(cooldown: const Duration(seconds: 2), batchInterval: Duration.zero);
    final item = detection('person', 0.50, 0.9);
    final start = DateTime.utc(2026, 1, 1);
    expect(engine.choose([item], now: start), isNotNull);
    expect(engine.choose([item], now: start.add(const Duration(seconds: 1))), isNull);
    expect(engine.choose([item], now: start.add(const Duration(seconds: 3))), isNotNull);
  });

  test('all bundled detector classes can trigger guidance', () {
    final engine = GuidanceEngine(batchInterval: Duration.zero);
    final event = engine.choose([detection('book', 0.8, 0.99)]);
    expect(event, isNotNull);
    expect(event!.detection.label, 'book');
  });

  test('chooseMany returns distinct exact objects instead of person-only guidance', () {
    final engine = GuidanceEngine(batchInterval: Duration.zero);
    final events = engine.chooseMany([
      detection('person', 0.55, 0.88),
      detection('chair', 0.52, 0.91, left: 0.02, right: 0.32),
      detection('bottle', 0.48, 0.87, left: 0.70, right: 0.95),
      detection('person', 0.30, 0.99),
    ], maxEvents: 3, now: DateTime.utc(2026, 1, 1));

    expect(events, hasLength(3));
    expect(events.map((event) => event.detection.label).toSet(), {'person', 'chair', 'bottle'});
    expect(events.first.detection.label, isNot(equals('person')));
  });

  test('spatial direction uses bounding-box center', () {
    expect(classifySpatialDirection(detection('book', 0.3, 0.9, left: 0.02, right: 0.22).box), SpatialDirection.left);
    expect(classifySpatialDirection(detection('book', 0.3, 0.9, left: 0.4, right: 0.6).box), SpatialDirection.center);
    expect(classifySpatialDirection(detection('book', 0.3, 0.9, left: 0.75, right: 0.95).box), SpatialDirection.right);
  });
}
