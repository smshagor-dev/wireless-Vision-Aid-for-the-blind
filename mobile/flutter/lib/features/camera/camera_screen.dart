import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/models/app_settings.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/ui_metrics.dart';
import '../../core/transport/esp32_frame_receiver.dart';
import '../../core/transport/udp_replay_store.dart';
import '../../core/vision/camera_tensor_preprocessor.dart';
import '../../core/vision/detection.dart';
import '../../core/vision/jpeg_tensor_preprocessor.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  static const _minimumInferenceInterval = Duration(milliseconds: 180);

  final _phonePreprocessor = const CameraTensorPreprocessor(inputSize: 320);
  final _jpegPreprocessor = const JpegTensorPreprocessor(inputSize: 320);
  CameraController? _cameraController;
  Esp32FrameReceiver? _esp32Receiver;
  StreamSubscription<Uint8List>? _esp32FrameSubscription;
  StreamSubscription<Esp32ReceiverStats>? _esp32StatsSubscription;
  Uint8List? _latestEsp32Jpeg;
  DateTime? _lastInferenceStarted;
  Duration? _lastInferenceDuration;
  List<Detection> _detections = const [];
  String? _error;
  bool _initializing = true;
  bool _processingFrame = false;
  bool _paused = false;
  bool _torchOn = false;
  bool _esp32Authenticated = false;

  bool get _usingPhone => widget.controller.settings.cameraSource == CameraSourceType.phone;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_startSelectedSource());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      unawaited(_stopSources());
    } else if (state == AppLifecycleState.resumed) {
      unawaited(_startSelectedSource());
    }
  }

  Future<void> _startSelectedSource() async {
    if (!mounted) return;
    setState(() {
      _initializing = true;
      _error = null;
      _paused = false;
      _torchOn = false;
      _esp32Authenticated = false;
      _latestEsp32Jpeg = null;
      _detections = const [];
      _lastInferenceDuration = null;
    });
    try {
      await widget.controller.ensureInferenceReady();
      if (_usingPhone) {
        await _startPhoneCamera();
      } else {
        await _startEsp32Receiver();
      }
      if (mounted) setState(() => _initializing = false);
    } catch (error) {
      await _stopSources();
      if (!mounted) return;
      setState(() {
        _initializing = false;
        _error = error.toString();
      });
    }
  }

  CameraDescription _selectCamera(List<CameraDescription> cameras) {
    for (final camera in cameras) {
      if (camera.lensDirection == CameraLensDirection.back) return camera;
    }
    return cameras.first;
  }

  Future<void> _startPhoneCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) throw CameraException('noCamera', 'No camera is available on this device.');
    final description = _selectCamera(cameras);
    final controller = CameraController(
      description,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );
    await controller.initialize();
    if (!mounted) {
      await controller.dispose();
      return;
    }
    _cameraController = controller;
    await controller.startImageStream((image) {
      unawaited(_processPhoneFrame(image, description.sensorOrientation));
    });
  }

  Future<void> _startEsp32Receiver() async {
    final credentials = widget.controller.esp32Credentials;
    if (credentials == null || !credentials.isConfigured) {
      throw FormatException(widget.controller.standaloneStrings.get('pairingRequired'));
    }
    final receiver = Esp32FrameReceiver(
      credentials: credentials,
      port: widget.controller.settings.esp32ListenPort,
      replayStore: SharedPreferencesUdpReplayStore(),
    );
    _esp32Receiver = receiver;
    _esp32FrameSubscription = receiver.frames.listen((jpeg) {
      if (!_paused && mounted) setState(() => _latestEsp32Jpeg = jpeg);
      unawaited(_processEsp32Frame(jpeg));
    });
    _esp32StatsSubscription = receiver.stats.listen((stats) {
      if (mounted) setState(() => _esp32Authenticated = stats.authenticated);
    });
    await receiver.start();
  }

  bool _canProcessFrame() {
    if (_paused || _processingFrame) return false;
    final now = DateTime.now();
    final previous = _lastInferenceStarted;
    if (previous != null && now.difference(previous) < _minimumInferenceInterval) return false;
    _lastInferenceStarted = now;
    _processingFrame = true;
    return true;
  }

  Future<void> _processPhoneFrame(CameraImage image, int rotationDegrees) async {
    if (!_canProcessFrame()) return;
    try {
      final tensor = _phonePreprocessor.preprocess(image, rotationDegrees: rotationDegrees);
      await _runInference(tensor);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _processEsp32Frame(Uint8List jpeg) async {
    if (!_canProcessFrame()) return;
    try {
      final tensor = _jpegPreprocessor.preprocess(jpeg);
      await _runInference(tensor);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _runInference(Float32List tensor) async {
    final result = await widget.controller.processTensor(tensor);
    if (!mounted) return;
    setState(() {
      _detections = result.detections;
      _lastInferenceDuration = result.inferenceDuration;
      _error = null;
    });
  }

  Future<void> _togglePause() async {
    final nextPaused = !_paused;
    final camera = _cameraController;
    try {
      if (_usingPhone && camera != null && camera.value.isInitialized) {
        if (nextPaused) {
          if (camera.value.isStreamingImages) await camera.stopImageStream();
          await camera.pausePreview();
        } else {
          await camera.resumePreview();
          if (!camera.value.isStreamingImages) {
            final rotation = camera.description.sensorOrientation;
            await camera.startImageStream((image) => unawaited(_processPhoneFrame(image, rotation)));
          }
        }
      }
      if (mounted) setState(() => _paused = nextPaused);
    } on CameraException catch (error) {
      if (mounted) setState(() => _error = error.description ?? error.code);
    }
  }

  Future<void> _toggleTorch() async {
    if (!_usingPhone) return;
    final camera = _cameraController;
    if (camera == null || !camera.value.isInitialized) return;
    try {
      final next = !_torchOn;
      await camera.setFlashMode(next ? FlashMode.torch : FlashMode.off);
      if (mounted) setState(() => _torchOn = next);
    } on CameraException {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(widget.controller.strings.get('flashUnavailable'))),
      );
    }
  }

  Future<void> _stopSources() async {
    final camera = _cameraController;
    _cameraController = null;
    if (camera != null) {
      try {
        if (camera.value.isStreamingImages) await camera.stopImageStream();
      } catch (_) {}
      await camera.dispose();
    }
    await _esp32FrameSubscription?.cancel();
    _esp32FrameSubscription = null;
    await _esp32StatsSubscription?.cancel();
    _esp32StatsSubscription = null;
    final receiver = _esp32Receiver;
    _esp32Receiver = null;
    if (receiver != null) await receiver.dispose();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(widget.controller.stopFeedback());
    unawaited(_stopSources());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final standalone = widget.controller.standaloneStrings;
    final camera = _cameraController;
    final sourceLabel = _usingPhone ? standalone.get('phoneCamera') : standalone.get('esp32Camera');
    final sourceActive = _usingPhone
        ? camera != null && camera.value.isInitialized
        : _esp32Authenticated;
    final runtimeReady = widget.controller.runtimeState == LocalRuntimeState.ready;
    final primaryDetection = _detections.isEmpty ? null : _detections.first;
    final proximity = primaryDetection == null ? null : classifyRelativeProximity(primaryDetection.box);

    return Scaffold(
      backgroundColor: AppTheme.navy,
      appBar: AppBar(
        titleSpacing: 4,
        title: Text(strings.get('assistance')),
        actions: [
          IconButton(
            tooltip: strings.get('torch'),
            onPressed: _usingPhone ? _toggleTorch : null,
            icon: Icon(_torchOn ? Icons.flash_on_rounded : Icons.flashlight_on_outlined),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Column(
          children: [
            Expanded(
              flex: 6,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Container(
                    key: const Key('assistance-camera-stage'),
                    color: Colors.black,
                    alignment: Alignment.center,
                    child: _buildPreview(camera, strings.get('cameraStarting')),
                  ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: _HudBadge(
                      key: const Key('assistance-inference-badge'),
                      text: _lastInferenceDuration == null ? 'AI: —' : 'AI: ${_lastInferenceDuration!.inMilliseconds} ms',
                    ),
                  ),
                  Positioned(
                    left: 12,
                    bottom: 12,
                    child: _HudBadge(
                      leadingColor: sourceActive ? AppTheme.greenBorder : const Color(0xFFFFA726),
                      text: sourceActive ? sourceLabel : (_usingPhone ? sourceLabel : 'ESP32 auth…'),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 5,
              child: Container(
                key: const Key('assistance-control-panel'),
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
                decoration: const BoxDecoration(
                  color: AppTheme.navy,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
                ),
                child: Column(
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
                      decoration: BoxDecoration(
                        color: runtimeReady ? const Color(0xFF0B231D) : const Color(0xFF160C18),
                        borderRadius: BorderRadius.circular(UiMetrics.cardRadius),
                        border: Border.all(color: runtimeReady ? const Color(0xFF15563E) : const Color(0xFF441525)),
                      ),
                      child: Row(
                        children: [
                          Icon(runtimeReady ? Icons.memory_rounded : Icons.shield_outlined,
                              color: runtimeReady ? AppTheme.greenBorder : const Color(0xFFFF5252), size: 27),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              _error ??
                                  (primaryDetection == null
                                      ? (runtimeReady ? standalone.get('runtimeReady') : standalone.get('runtimeStarting'))
                                      : standalone.guidanceMessage(primaryDetection.label, proximity!)),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700, height: 1.3),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(child: _InfoChip(icon: _usingPhone ? Icons.smartphone_rounded : Icons.wifi_tethering_rounded, label: standalone.get('cameraSource'), value: sourceLabel)),
                        const SizedBox(width: 10),
                        Expanded(child: _InfoChip(icon: Icons.center_focus_strong_rounded, label: strings.get('detection'), value: '${_detections.length}')),
                      ],
                    ),
                    const Spacer(),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _RoundAction(
                          icon: _paused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                          label: _paused ? strings.get('resume') : strings.get('pause'),
                          onTap: _togglePause,
                        ),
                        _RoundAction(
                          icon: Icons.stop_rounded,
                          label: strings.get('stop'),
                          fill: AppTheme.red,
                          border: const Color(0xFFFF5A61),
                          onTap: () => Navigator.of(context).pop(),
                        ),
                        _RoundAction(
                          icon: _torchOn ? Icons.flash_on_rounded : Icons.flashlight_on_outlined,
                          label: strings.get('torch'),
                          active: _torchOn,
                          disabled: !_usingPhone,
                          onTap: _toggleTorch,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreview(CameraController? camera, String loadingText) {
    if (_initializing) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(width: 34, height: 34, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3)),
          const SizedBox(height: 14),
          Text(loadingText, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
        ],
      );
    }
    if (_error != null && (_usingPhone ? camera == null : _latestEsp32Jpeg == null)) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 52),
            const SizedBox(height: 14),
            Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 18),
            OutlinedButton(onPressed: _startSelectedSource, style: OutlinedButton.styleFrom(foregroundColor: Colors.white), child: const Text('Retry')),
          ],
        ),
      );
    }
    if (_usingPhone && camera != null && camera.value.isInitialized) {
      return CameraPreview(camera);
    }
    final jpeg = _latestEsp32Jpeg;
    if (!_usingPhone && jpeg != null) {
      return Image.memory(jpeg, fit: BoxFit.cover, gaplessPlayback: true);
    }
    return Text(_usingPhone ? 'Camera unavailable' : 'Waiting for authenticated ESP32-CAM frames…',
        textAlign: TextAlign.center, style: const TextStyle(color: Colors.white));
  }
}

class _HudBadge extends StatelessWidget {
  const _HudBadge({super.key, required this.text, this.leadingColor});
  final String text;
  final Color? leadingColor;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: const Color(0xB20A1022),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (leadingColor != null) ...[
              Container(width: 8, height: 8, decoration: BoxDecoration(color: leadingColor, shape: BoxShape.circle)),
              const SizedBox(width: 7),
            ],
            Text(text, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
          ],
        ),
      );
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minHeight: 52),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0B1A3B),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF17315F)),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.cyan, size: 21),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(color: Color(0xFF8EA2C9), fontSize: 11, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 1),
                  Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _RoundAction extends StatelessWidget {
  const _RoundAction({
    required this.icon,
    required this.label,
    required this.onTap,
    this.fill,
    this.border,
    this.active = false,
    this.disabled = false,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? fill;
  final Color? border;
  final bool active;
  final bool disabled;

  @override
  Widget build(BuildContext context) {
    final background = fill ?? (active ? const Color(0xFF114C70) : const Color(0xFF172443));
    return Opacity(
      opacity: disabled ? 0.42 : 1,
      child: Column(
        children: [
          InkWell(
            customBorder: const CircleBorder(),
            onTap: disabled ? null : onTap,
            child: Container(
              width: UiMetrics.cameraActionDiameter,
              height: UiMetrics.cameraActionDiameter,
              decoration: BoxDecoration(
                color: background,
                shape: BoxShape.circle,
                border: Border.all(color: border ?? const Color(0xFF26385E)),
                boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 8, offset: Offset(0, 4))],
              ),
              child: Icon(icon, color: Colors.white, size: 29),
            ),
          ),
          const SizedBox(height: 7),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
