import 'dart:typed_data';

import 'package:image/image.dart' as img;

class JpegTensorPreprocessor {
  const JpegTensorPreprocessor({this.inputSize = 320});

  final int inputSize;

  Float32List preprocess(Uint8List jpegBytes) {
    final image = img.decodeJpg(jpegBytes);
    if (image == null || image.width <= 0 || image.height <= 0) {
      throw const FormatException('ESP32 frame is not a valid JPEG image.');
    }
    final scale = inputSize / (image.width > image.height ? image.width : image.height);
    final contentWidth = image.width * scale;
    final contentHeight = image.height * scale;
    final padX = (inputSize - contentWidth) / 2;
    final padY = (inputSize - contentHeight) / 2;
    final pixels = inputSize * inputSize;
    final tensor = Float32List(pixels * 3);
    const padding = 114 / 255.0;
    tensor.fillRange(0, tensor.length, padding);

    for (var y = 0; y < inputSize; y++) {
      final sourceY = (y - padY) / scale;
      if (sourceY < 0 || sourceY >= image.height) continue;
      for (var x = 0; x < inputSize; x++) {
        final sourceX = (x - padX) / scale;
        if (sourceX < 0 || sourceX >= image.width) continue;
        final pixel = image.getPixel(
          sourceX.floor().clamp(0, image.width - 1),
          sourceY.floor().clamp(0, image.height - 1),
        );
        final index = y * inputSize + x;
        tensor[index] = pixel.r.toDouble() / 255.0;
        tensor[pixels + index] = pixel.g.toDouble() / 255.0;
        tensor[2 * pixels + index] = pixel.b.toDouble() / 255.0;
      }
    }
    return tensor;
  }
}
