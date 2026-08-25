import 'dart:typed_data';

import 'package:camera/camera.dart';

class CameraTensorPreprocessor {
  const CameraTensorPreprocessor({this.inputSize = 320});

  final int inputSize;

  Float32List preprocess(CameraImage image, {required int rotationDegrees}) {
    if (image.planes.length < 3) {
      throw StateError('WVAB requires Android YUV420 camera frames.');
    }
    final rotation = ((rotationDegrees % 360) + 360) % 360;
    if (rotation != 0 && rotation != 90 && rotation != 180 && rotation != 270) {
      throw ArgumentError.value(rotationDegrees, 'rotationDegrees', 'Rotation must be 0, 90, 180, or 270.');
    }

    final sourceWidth = image.width;
    final sourceHeight = image.height;
    final orientedWidth = rotation == 90 || rotation == 270 ? sourceHeight : sourceWidth;
    final orientedHeight = rotation == 90 || rotation == 270 ? sourceWidth : sourceHeight;
    final scale = inputSize / (orientedWidth > orientedHeight ? orientedWidth : orientedHeight);
    final contentWidth = orientedWidth * scale;
    final contentHeight = orientedHeight * scale;
    final padX = (inputSize - contentWidth) / 2;
    final padY = (inputSize - contentHeight) / 2;
    final pixels = inputSize * inputSize;
    final tensor = Float32List(3 * pixels);
    const padding = 114 / 255.0;
    tensor.fillRange(0, tensor.length, padding);

    final yPlane = image.planes[0];
    final uPlane = image.planes[1];
    final vPlane = image.planes[2];
    final uvPixelStride = uPlane.bytesPerPixel ?? 1;

    for (var targetY = 0; targetY < inputSize; targetY++) {
      final oy = (targetY - padY) / scale;
      if (oy < 0 || oy >= orientedHeight) continue;
      for (var targetX = 0; targetX < inputSize; targetX++) {
        final ox = (targetX - padX) / scale;
        if (ox < 0 || ox >= orientedWidth) continue;
        final source = _sourceCoordinate(
          ox.floor(),
          oy.floor(),
          sourceWidth,
          sourceHeight,
          rotation,
        );
        final sx = source.$1.clamp(0, sourceWidth - 1);
        final sy = source.$2.clamp(0, sourceHeight - 1);

        final yIndex = sy * yPlane.bytesPerRow + sx;
        final uvIndex = (sy ~/ 2) * uPlane.bytesPerRow + (sx ~/ 2) * uvPixelStride;
        if (yIndex >= yPlane.bytes.length || uvIndex >= uPlane.bytes.length || uvIndex >= vPlane.bytes.length) {
          continue;
        }
        final yValue = yPlane.bytes[yIndex].toDouble();
        final uValue = uPlane.bytes[uvIndex].toDouble() - 128.0;
        final vValue = vPlane.bytes[uvIndex].toDouble() - 128.0;
        final r = (yValue + 1.402 * vValue).clamp(0.0, 255.0) / 255.0;
        final g = (yValue - 0.344136 * uValue - 0.714136 * vValue).clamp(0.0, 255.0) / 255.0;
        final b = (yValue + 1.772 * uValue).clamp(0.0, 255.0) / 255.0;
        final index = targetY * inputSize + targetX;
        tensor[index] = r;
        tensor[pixels + index] = g;
        tensor[2 * pixels + index] = b;
      }
    }
    return tensor;
  }

  (int, int) _sourceCoordinate(
    int x,
    int y,
    int sourceWidth,
    int sourceHeight,
    int rotation,
  ) {
    return switch (rotation) {
      0 => (x, y),
      90 => (y, sourceHeight - 1 - x),
      180 => (sourceWidth - 1 - x, sourceHeight - 1 - y),
      270 => (sourceWidth - 1 - y, x),
      _ => throw StateError('Unsupported rotation'),
    };
  }
}
