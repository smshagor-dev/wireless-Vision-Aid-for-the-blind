import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/models/app_settings.dart';
import 'package:wvab_mobile/core/vision/coco_labels.dart';

void main() {
  test('mobile defaults enable every bundled COCO detector class', () {
    final settings = const AppSettings();

    expect(coco80Labels, hasLength(80));
    expect(settings.detectedClasses, hasLength(80));
    expect(settings.detectedClasses, equals(coco80Labels.toSet()));
  });

  test('legacy mobile class set is a strict subset of the full detector', () {
    expect(legacyDetectedClassesV1.length, 11);
    expect(allCocoDetectedClasses.containsAll(legacyDetectedClassesV1), isTrue);
    expect(allCocoDetectedClasses.length, greaterThan(legacyDetectedClassesV1.length));
  });
}
