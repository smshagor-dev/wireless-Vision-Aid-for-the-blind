import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/vision/detection.dart';
import 'package:wvab_mobile/core/vision/guidance_engine.dart';

void main() {
  Detection detection(String label, double height, double confidence) => Detection(
        classId: 0,
        label: label,
        confidence: confidence,
        box: BoundingBox(left: 0.2, top: 0.1, right: 0.8, bottom: 0.1 + height),
      );

  test('immediate hazards outrank farther hazards', () {
    final engine = GuidanceEngine();
    final event = engine.choose([
      detection('car', 0.25, 0.95),
      detection('person', 0.70, 0.80),
    ], now: DateTime.utc(2026, 1, 1));
    expect(event, isNotNull);
    expect(event!.detection.label, 'person');
    expect(event.proximity, ProximityBand.immediate);
    expect(event.urgent, isTrue);
  });

  test('cooldown suppresses repeated announcements', () {
    final engine = GuidanceEngine(cooldown: const Duration(seconds: 2));
    final item = detection('person', 0.50, 0.9);
    final start = DateTime.utc(2026, 1, 1);
    expect(engine.choose([item], now: start), isNotNull);
    expect(engine.choose([item], now: start.add(const Duration(seconds: 1))), isNull);
    expect(engine.choose([item], now: start.add(const Duration(seconds: 3))), isNotNull);
  });

  test('non-policy classes do not trigger guidance', () {
    final engine = GuidanceEngine();
    expect(engine.choose([detection('book', 0.8, 0.99)]), isNull);
  });
}
