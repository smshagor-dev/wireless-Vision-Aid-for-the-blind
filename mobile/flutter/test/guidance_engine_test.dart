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

  test('focuses the visibly nearer object without class bias', () {
    final engine = GuidanceEngine(cooldown: Duration.zero);
    final event = engine.choose([
      detection('car', 0.25, 0.95),
      detection('book', 0.59, 0.80, left: 0.05, right: 0.32),
      detection('person', 0.52, 0.99, left: 0.35, right: 0.65),
    ], now: DateTime.utc(2026, 1, 1));
    expect(event, isNotNull);
    expect(event!.detection.label, 'book');
    expect(event.proximity, ProximityBand.close);
  });

  test('same focused hazard is held briefly when no more urgent hazard appears', () {
    final engine = GuidanceEngine(cooldown: Duration.zero, focusHold: const Duration(seconds: 2));
    final start = DateTime.utc(2026, 1, 1);
    expect(engine.choose([
      detection('chair', 0.55, 0.90),
      detection('person', 0.45, 0.99),
    ], now: start)!.detection.label, 'chair');

    expect(engine.choose([
      detection('chair', 0.50, 0.80),
      detection('person', 0.58, 0.99),
    ], now: start.add(const Duration(seconds: 1)))!.detection.label, 'chair');
  });

  test('new immediate hazard preempts an older close focus', () {
    final engine = GuidanceEngine(cooldown: Duration.zero, focusHold: const Duration(seconds: 2));
    final start = DateTime.utc(2026, 1, 1);
    expect(engine.choose([
      detection('chair', 0.50, 0.90),
      detection('person', 0.45, 0.99),
    ], now: start)!.detection.label, 'chair');

    final next = engine.choose([
      detection('chair', 0.48, 0.80),
      detection('car', 0.72, 0.95),
    ], now: start.add(const Duration(seconds: 1)));
    expect(next, isNotNull);
    expect(next!.detection.label, 'car');
    expect(next.proximity, ProximityBand.immediate);
  });

  test('side obstacle recommends the clearer opposite side', () {
    final engine = GuidanceEngine(cooldown: Duration.zero);
    final event = engine.choose([
      detection('chair', 0.55, 0.95, left: 0.02, right: 0.32),
    ]);
    expect(event, isNotNull);
    expect(event!.direction, SpatialDirection.left);
    expect(event.navigationCue, NavigationCue.moveRight);
  });

  test('fully blocked close scene recommends stop', () {
    final engine = GuidanceEngine(cooldown: Duration.zero);
    final event = engine.choose([
      detection('person', 0.75, 0.95, left: 0.00, right: 0.34),
      detection('chair', 0.75, 0.92, left: 0.33, right: 0.67),
      detection('car', 0.75, 0.90, left: 0.66, right: 1.00),
    ]);
    expect(event, isNotNull);
    expect(event!.navigationCue, NavigationCue.stop);
    expect(event.urgent, isTrue);
  });

  test('metric estimate is available only for reference-size classes', () {
    final person = detection('person', 0.50, 0.9);
    final book = detection('book', 0.50, 0.9);
    expect(estimateApproximateDistanceMeters(person), isNotNull);
    expect(estimateApproximateDistanceMeters(person)!, greaterThan(2.0));
    expect(estimateApproximateDistanceMeters(book), isNull);
  });

  test('all bundled detector classes can still become the focused object', () {
    final engine = GuidanceEngine(cooldown: Duration.zero);
    final event = engine.choose([detection('book', 0.8, 0.99)]);
    expect(event, isNotNull);
    expect(event!.detection.label, 'book');
  });
}
