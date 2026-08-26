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
import '../../core/vision/vision_input.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  static const _minimumInferenceInterval = Duration(milliseconds: 300);
  static const _previewSettleDelay = Duration(milliseconds: 120);

  final _phonePreprocessor = const CameraTensorPreprocessor(inputSize: 320);
  final _jpegPreprocessor = const JpegTensorPreprocessor(inputSize: 320);

  CameraController? _cameraController;
  Esp32FrameReceiver? _esp32Receiver;
  StreamSubscription<Uint8List>? _esp32FrameSubscription;
  StreamSubscription<Esp32ReceiverStats>? _esp32StatsSubscription;
  Future<void> _sourceTransition = Future<void>.value();

  Uint8List? _latestEsp32Jpeg;
  DateTime? _lastInferenceStarted;
  Duration? _lastInferenceDuration;
  List<Detection> _detections = const [];
  String? _error;

  int _sourceGeneration = 0;
  bool _wantSourceRunning = false;
  bool _disposed = false;
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
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _requestSourceStart();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _requestSourceStart();
        break;
      case AppLifecycleState.inactive:
      case AppLifecycleState.paused:
      case AppLifecycleState.hidden:
      case AppLifecycleState.detached:
        _requestSourceStop();
        break;
    }
  }

  void _requestSourceStart() {
    if (_disposed) return;
    _wantSourceRunning = true;
    final generation = ++_sourceGeneration;
    _enqueueSourceTransition(() => _startSelectedSource(generation));
  }

  void _requestSourceStop() {
    _wantSourceRunning = false;
    ++_sourceGeneration;
    _enqueueSourceTransition(_stopSourcesInternal);
  }

  void _enqueueSourceTransition(Future<void> Function() operation) {
    final next = _sourceTransition.then((_) => operation());
    _sourceTransition = next.catchError((Object error, StackTrace stackTrace) {
      debugPrint('WVAB camera transition failed: $error\n$stackTrace');
    });
  }

  bool _isCurrentSource(int generation) {
    return mounted && !_disposed && _wantSourceRunning && generation == _sourceGeneration;
  }

  void _resetViewForStart() {
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
  }

  Future<void> _startSelectedSource(int generation) async {
    if (!_isCurrentSource(generation)) return;
    await _stopSourcesInternal();
    if (!_isCurrentSource(generation)) return;

    _resetViewForStart();
    try {
      if (_usingPhone) {
        await _startPhoneCamera(generation);
      } else {
        await _startEsp32Receiver(generation);
      }
    } catch (error, stackTrace) {
      debugPrint('WVAB source startup failed: $error\n$stackTrace');
      await _stopSourcesInternal();
      if (!_isCurrentSource(generation)) return;
      setState(() {
        _initializing = false;
        _error = _friendlyCameraError(error);
      });
    }
  }

  String _friendlyCameraError(Object error) {
    if (error is CameraException) {
      return switch (error.code) {
        'CameraAccessDenied' => 'Camera permission was denied. Allow camera access and retry.',
        'CameraAccessDeniedWithoutPrompt' => 'Camera access is disabled. Enable it in Android settings and retry.',
        _ => error.description ?? error.code,
      };
    }
    return error.toString();
  }

  CameraDescription _selectCamera(List<CameraDescription> cameras) {
    for (final camera in cameras) {
      if (camera.lensDirection == CameraLensDirection.back) return camera;
    }
    return cameras.first;
  }

  Future<void> _startPhoneCamera(int generation) async {
    final cameras = await availableCameras();
    if (!_isCurrentSource(generation)) return;
    if (cameras.isEmpty) {
      throw CameraException('noCamera', 'No camera is available on this device.');
    }

    final description = _selectCamera(cameras);
    final controller = CameraController(
      description,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );

    try {
      await controller.initialize();
      if (!_isCurrentSource(generation)) {
        await _safeDisposeCamera(controller);
        return;
      }

      _cameraController = controller;
      if (mounted) {
        setState(() {
          _initializing = false;
          _error = null;
        });
      }

      await Future<void>.delayed(_previewSettleDelay);
      if (!_isCurrentSource(generation) || !identical(_cameraController, controller)) {
        if (!identical(_cameraController, controller)) {
          await _safeDisposeCamera(controller);
        }
        return;
      }

      // Initialize native inference only after the camera preview is stable. This
      // keeps camera permission/lifecycle transitions independent from ONNX setup.
      await widget.controller.ensureInferenceReady();
      if (!_isCurrentSource(generation) || !identical(_cameraController, controller)) return;

      await controller.startImageStream((image) {
        if (!_isCurrentSource(generation) || _paused) return;
        unawaited(_processPhoneFrame(image, description.sensorOrientation, generation));
      });
    } catch (_) {
      if (identical(_cameraController, controller)) _cameraController = null;
      await _safeDisposeCamera(controller);
      rethrow;
    }
  }

  Future<void> _startEsp32Receiver(int generation) async {
    final credentials = widget.controller.esp32Credentials;
    if (credentials == null || !credentials.isConfigured) {
      throw FormatException(widget.controller.standaloneStrings.get('pairingRequired'));
    }

    final receiver = Esp32FrameReceiver(
      credentials: credentials,
      port: widget.controller.settings.esp32ListenPort,
      replayStore: SharedPreferencesUdpReplayStore(),
    );

    await receiver.start();
    if (!_isCurrentSource(generation)) {
      await receiver.dispose();
      return;
    }

    _esp32Receiver = receiver;
    _esp32FrameSubscription = receiver.frames.listen((jpeg) {
      if (!_isCurrentSource(generation)) return;
      if (!_paused && mounted) setState(() => _latestEsp32Jpeg = jpeg);
      unawaited(_processEsp32Frame(jpeg, generation));
    });
    _esp32StatsSubscription = receiver.stats.listen((stats) {
      if (_isCurrentSource(generation) && mounted) {
        setState(() => _esp32Authenticated = stats.authenticated);
      }
    });

    if (mounted) setState(() => _initializing = false);
    await widget.controller.ensureInferenceReady();
  }

  bool _canProcessFrame(int generation) {
    if (!_isCurrentSource(generation) || _paused || _processingFrame) return false;
    final now = DateTime.now();
    final previous = _lastInferenceStarted;
    if (previous != null && now.difference(previous) < _minimumInferenceInterval) return false;
    _lastInferenceStarted = now;
    _processingFrame = true;
    return true;
  }

  Future<void> _processPhoneFrame(CameraImage image, int rotationDegrees, int generation) async {
    if (!_canProcessFrame(generation)) return;
    try {
      final prepared = _phonePreprocessor.preprocess(image, rotationDegrees: rotationDegrees);
      await _runInference(prepared, generation);
    } catch (error, stackTrace) {
      debugPrint('WVAB phone-frame processing failed: $error\n$stackTrace');
      if (_isCurrentSource(generation) && mounted) setState(() => _error = error.toString());
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _processEsp32Frame(Uint8List jpeg, int generation) async {
    if (!_canProcessFrame(generation)) return;
    try {
      final prepared = _jpegPreprocessor.preprocess(jpeg);
      await _runInference(prepared, generation);
    } catch (error, stackTrace) {
      debugPrint('WVAB ESP32-frame processing failed: $error\n$stackTrace');
      if (_isCurrentSource(generation) && mounted) setState(() => _error = error.toString());
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _runInference(PreparedVisionInput prepared, int generation) async {
    final result = await widget.controller.processTensor(
      prepared.tensor,
      transform: prepared.transform,
    );
    if (!_isCurrentSource(generation) || !mounted) return;
    setState(() {
      _detections = result.detections;
      _lastInferenceDuration = result.inferenceDuration;
      _error = null;
    });
  }

  Future<void> _togglePause() async {
    if (_disposed) return;
    final nextPaused = !_paused;
    final camera = _cameraController;
    final generation = _sourceGeneration;
    try {
      if (_usingPhone && camera != null && _isCurrentSource(generation)) {
        if (nextPaused) {
          if (camera.value.isStreamingImages) await camera.stopImageStream();
          if (_isCurrentSource(generation)) await camera.pausePreview();
        } else {
          await camera.resumePreview();
          if (_isCurrentSource(generation) && !camera.value.isStreamingImages) {
            final rotation = camera.description.sensorOrientation;
            await camera.startImageStream((image) {
              if (!_isCurrentSource(generation) || _paused) return;
              unawaited(_processPhoneFrame(image, rotation, generation));
            });
          }
        }
      }
      if (mounted && _isCurrentSource(generation)) setState(() => _paused = nextPaused);
    } on CameraException catch (error) {
      if (mounted && _isCurrentSource(generation)) {
        setState(() => _error = error.description ?? error.code);
      }
    }
  }

  Future<void> _toggleTorch() async {
    if (!_usingPhone || _disposed) return;
    final camera = _cameraController;
    final generation = _sourceGeneration;
    if (camera == null || !_isCurrentSource(generation)) return;
    try {
      final next = !_torchOn;
      await camera.setFlashMode(next ? FlashMode.torch : FlashMode.off);
      if (mounted && _isCurrentSource(generation)) setState(() => _torchOn = next);
    } on CameraException {
      if (!mounted || !_isCurrentSource(generation)) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(widget.controller.strings.get('flashUnavailable'))),
      );
    }
  }

  Future<void> _safeDisposeCamera(CameraController camera) async {
    try {
      if (camera.value.isStreamingImages) await camera.stopImageStream();
    } catch (_) {}
    try {
      await camera.dispose();
    } catch (error, stackTrace) {
      debugPrint('WVAB camera dispose failed: $error\n$stackTrace');
    }
  }

  Future<void> _stopSourcesInternal() async {
    _processingFrame = false;

    final camera = _cameraController;
    _cameraController = null;
    if (camera != null) await _safeDisposeCamera(camera);

    final frameSubscription = _esp32FrameSubscription;
    _esp32FrameSubscription = null;
    if (frameSubscription != null) {
      try {
        await frameSubscription.cancel();
      } catch (_) {}
    }

    final statsSubscription = _esp32StatsSubscription;
    _esp32StatsSubscription = null;
    if (statsSubscription != null) {
      try {
        await statsSubscription.cancel();
      } catch (_) {}
    }

    final receiver = _esp32Receiver;
    _esp32Receiver = null;
    if (receiver != null) {
      try {
        await receiver.dispose();
      } catch (error, stackTrace) {
        debugPrint('WVAB ESP32 receiver dispose failed: $error\n$stackTrace');
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _wantSourceRunning = false;
    ++_sourceGeneration;
    WidgetsBinding.instance.removeObserver(this);
    unawaited(widget.controller.stopFeedback());
    _enqueueSourceTransition(_stopSourcesInternal);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final standalone = widget.controller.standaloneStrings;
    final camera = _cameraController;
    final sourceLabel = _usingPhone ? standalone.get('phoneCamera') : standalone.get('esp32Camera');
    final sourceActive = _usingPhone ? camera != null && camera.value.isInitialized : _esp32Authenticated;
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
                          Icon(
                            runtimeReady ? Icons.memory_rounded : Icons.shield_outlined,
                            color: runtimeReady ? AppTheme.greenBorder : const Color(0xFFFF5252),
                            size: 27,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              _error ??
                                  (primaryDetection == null
                                      ? (runtimeReady ? standalone.get('runtimeReady') : standalone.get('runtimeStarting'))
                                      : standalone.guidanceMessage(primaryDetection.label, proximity!)),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                height: 1.3,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _InfoChip(
                            icon: _usingPhone ? Icons.smartphone_rounded : Icons.wifi_tethering_rounded,
                            label: standalone.get('cameraSource'),
                            value: sourceLabel,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _InfoChip(
                            icon: Icons.center_focus_strong_rounded,
                            label: strings.get('detection'),
                            value: '${_detections.length}',
                          ),
                        ),
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
          const SizedBox(
            width: 34,
            height: 34,
            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
          ),
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
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 18),
            OutlinedButton(
              onPressed: _requestSourceStart,
              style: OutlinedButton.styleFrom(foregroundColor: Colors.white),
              child: const Text('Retry'),
            ),
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
    return Text(
      _usingPhone ? 'Camera unavailable' : 'Waiting for authenticated ESP32-CAM frames…',
      textAlign: TextAlign.center,
      style: const TextStyle(color: Colors.white),
    );
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
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: leadingColor, shape: BoxShape.circle),
              ),
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
                  Text(
                    label,
                    style: const TextStyle(color: Color(0xFF8EA2C9), fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800),
                  ),
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
