import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';
import '../../core/theme/app_theme.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  CameraController? _cameraController;
  String? _error;
  bool _initializing = true;
  bool _paused = false;
  bool _torchOn = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final camera = _cameraController;
    if (camera == null || !camera.value.isInitialized) return;
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _disposeCamera();
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera();
    }
  }

  CameraDescription _selectCamera(List<CameraDescription> cameras) {
    for (final camera in cameras) {
      if (camera.lensDirection == CameraLensDirection.back) return camera;
    }
    return cameras.first;
  }

  Future<void> _initializeCamera() async {
    if (mounted) {
      setState(() {
        _initializing = true;
        _error = null;
        _paused = false;
        _torchOn = false;
      });
    }
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw CameraException('noCamera', 'No camera is available on this device.');
      }
      final controller = CameraController(
        _selectCamera(cameras),
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      await _cameraController?.dispose();
      setState(() {
        _cameraController = controller;
        _initializing = false;
      });
    } on CameraException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.description ?? error.code;
        _initializing = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = widget.controller.strings.get('cameraUnavailable');
        _initializing = false;
      });
    }
  }

  Future<void> _togglePause() async {
    final camera = _cameraController;
    if (camera == null || !camera.value.isInitialized) return;
    try {
      if (_paused) {
        await camera.resumePreview();
      } else {
        await camera.pausePreview();
      }
      if (mounted) setState(() => _paused = !_paused);
    } on CameraException {
      if (mounted) setState(() => _error = widget.controller.strings.get('cameraUnavailable'));
    }
  }

  Future<void> _toggleTorch() async {
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

  Future<void> _disposeCamera() async {
    final controller = _cameraController;
    _cameraController = null;
    if (controller != null) await controller.dispose();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.controller.stopFeedback();
    _disposeCamera();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = widget.controller.strings;
    final camera = _cameraController;
    return Scaffold(
      backgroundColor: AppTheme.navy,
      appBar: AppBar(
        title: Text(strings.get('assistance')),
        actions: [
          IconButton(onPressed: _toggleTorch, icon: Icon(_torchOn ? Icons.flash_on : Icons.flashlight_on_outlined)),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              flex: 6,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Container(
                    color: Colors.black,
                    alignment: Alignment.center,
                    child: _initializing
                        ? Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const CircularProgressIndicator(color: Colors.white),
                              const SizedBox(height: 14),
                              Text(strings.get('cameraStarting'), style: const TextStyle(color: Colors.white)),
                            ],
                          )
                        : _error != null
                            ? Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.videocam_off_outlined, color: Colors.white, size: 52),
                                    const SizedBox(height: 14),
                                    Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 18)),
                                    const SizedBox(height: 18),
                                    OutlinedButton(
                                      onPressed: _initializeCamera,
                                      child: Text(strings.get('restartCamera')),
                                    ),
                                  ],
                                ),
                              )
                            : camera != null && camera.value.isInitialized
                                ? Semantics(
                                    image: true,
                                    label: 'Live rear camera preview',
                                    child: CameraPreview(camera),
                                  )
                                : Text(strings.get('cameraUnavailable'), style: const TextStyle(color: Colors.white)),
                  ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(12)),
                      child: const Text('FPS: —', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 5,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
                decoration: const BoxDecoration(
                  color: Color(0xFF07112F),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                ),
                child: Column(
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF160C18),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFF441525)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.shield_outlined, color: Color(0xFFFF5252), size: 30),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              strings.get('inferencePending'),
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, height: 1.3),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(child: _InfoChip(icon: Icons.dns_outlined, label: strings.get('mode'), value: strings.get('edgeServer'))),
                        const SizedBox(width: 10),
                        Expanded(child: _InfoChip(icon: Icons.speed_rounded, label: strings.get('speed'), value: strings.get('normal'))),
                      ],
                    ),
                    const Spacer(),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _RoundAction(
                          icon: _paused ? Icons.play_arrow_rounded : Icons.volume_up_rounded,
                          label: _paused ? strings.get('resume') : strings.get('pause'),
                          onTap: _togglePause,
                        ),
                        _RoundAction(
                          icon: Icons.stop_rounded,
                          label: strings.get('stop'),
                          fill: AppTheme.red,
                          onTap: () => Navigator.of(context).pop(),
                        ),
                        _RoundAction(
                          icon: _torchOn ? Icons.flash_on : Icons.flashlight_on_outlined,
                          label: strings.get('torch'),
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
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label, required this.value});

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: const Color(0xFF38BDF8), size: 22),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(color: Color(0xFF8EA2C9), fontSize: 12)),
              Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ],
    );
  }
}

class _RoundAction extends StatelessWidget {
  const _RoundAction({required this.icon, required this.label, required this.onTap, this.fill});

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? fill;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: Container(
            width: 62,
            height: 62,
            decoration: BoxDecoration(color: fill ?? const Color(0xFF172443), shape: BoxShape.circle),
            child: Icon(icon, color: Colors.white, size: 30),
          ),
        ),
        const SizedBox(height: 7),
        Text(label, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
