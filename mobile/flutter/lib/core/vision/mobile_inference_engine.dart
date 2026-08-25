import 'dart:typed_data';

import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

import 'detection.dart';
import 'yolo_v8_parser.dart';

class MobileInferenceResult {
  const MobileInferenceResult({required this.detections, required this.inferenceDuration});

  final List<Detection> detections;
  final Duration inferenceDuration;
}

abstract class InferenceEngine {
  bool get isReady;
  Future<void> initialize();
  Future<MobileInferenceResult> run(Float32List nchwInput, {required double confidenceThreshold});
  Future<void> close();
}

class OnnxMobileInferenceEngine implements InferenceEngine {
  OnnxMobileInferenceEngine({
    this.assetPath = 'assets/models/yolov8n_320.onnx',
    this.inputSize = 320,
    YoloV8Parser parser = const YoloV8Parser(),
  }) : _parser = parser;

  final String assetPath;
  final int inputSize;
  final YoloV8Parser _parser;
  final OnnxRuntime _runtime = OnnxRuntime();
  OrtSession? _session;

  @override
  bool get isReady => _session != null;

  @override
  Future<void> initialize() async {
    if (_session != null) return;
    final available = await _runtime.getAvailableProviders();
    final providers = <OrtProvider>[
      if (available.contains(OrtProvider.NNAPI)) OrtProvider.NNAPI,
      if (available.contains(OrtProvider.XNNPACK)) OrtProvider.XNNPACK,
      OrtProvider.CPU,
    ];
    _session = await _runtime.createSessionFromAsset(
      assetPath,
      options: OrtSessionOptions(
        providers: providers.toSet().toList(),
        intraOpNumThreads: 2,
        interOpNumThreads: 1,
        useArena: true,
      ),
    );
    if (_session!.inputNames.isEmpty || _session!.outputNames.isEmpty) {
      await close();
      throw StateError('WVAB ONNX model has no usable inputs or outputs.');
    }
  }

  @override
  Future<MobileInferenceResult> run(
    Float32List nchwInput, {
    required double confidenceThreshold,
  }) async {
    final session = _session;
    if (session == null) throw StateError('WVAB inference engine is not initialized.');
    final expectedLength = 3 * inputSize * inputSize;
    if (nchwInput.length != expectedLength) {
      throw ArgumentError.value(nchwInput.length, 'nchwInput.length', 'Expected $expectedLength floats.');
    }

    final input = await OrtValue.fromList(nchwInput, [1, 3, inputSize, inputSize]);
    final stopwatch = Stopwatch()..start();
    Map<String, OrtValue>? outputs;
    try {
      outputs = await session.run({session.inputNames.first: input});
      stopwatch.stop();
      final output = outputs[session.outputNames.first];
      if (output == null) throw StateError('WVAB ONNX model did not produce its primary output.');
      final flat = await output.asFlattenedList();
      final detections = _parser.parse(
        values: flat.cast<num>(),
        shape: output.shape,
        inputSize: inputSize,
        confidenceThreshold: confidenceThreshold,
      );
      return MobileInferenceResult(detections: detections, inferenceDuration: stopwatch.elapsed);
    } finally {
      await input.dispose();
      if (outputs != null) {
        for (final value in outputs.values) {
          await value.dispose();
        }
      }
    }
  }

  @override
  Future<void> close() async {
    final session = _session;
    _session = null;
    if (session != null) await session.close();
  }
}
