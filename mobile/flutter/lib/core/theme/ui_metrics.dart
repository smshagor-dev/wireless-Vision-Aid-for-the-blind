import 'package:flutter/widgets.dart';

/// Canonical measurements for the approved WVAB mobile visual system.
///
/// Screens may scale down slightly on compact devices, but these values are
/// the reference proportions used by the mockup and the primary phone layout.
class UiMetrics {
  const UiMetrics._();

  static const double pageHorizontal = 22;
  static const double lightPageHorizontal = 20;
  static const double cardRadius = 18;
  static const double compactRadius = 14;
  static const double statusRadius = 18;
  static const double homeActionDiameter = 168;
  static const double homeTileHeight = 102;
  static const double cameraActionDiameter = 62;
  static const double controlHeight = 56;
  static const double settingsBottomBarHeight = 66;

  static const EdgeInsets homePadding = EdgeInsets.fromLTRB(22, 8, 22, 14);
  static const EdgeInsets lightPagePadding = EdgeInsets.fromLTRB(20, 18, 20, 22);
}
