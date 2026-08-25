import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../core/controllers/app_controller.dart';

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

  Future<void> _initializeCamera() async {
    if (mounted) {
      setState(() {
        _initializing = true;
        _error = null;
      });
    }

    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw const CameraException('noCamera', 'No camera is available on this device.');
      }

      final selected = cameras.cast<CameraDescription?>().firstWhere(
            (camera) => camera?.lensDirection == CameraLensDirection.back,
            orElse: () => cameras.first,
          ) ??
          cameras.first;

      final controller = CameraController(
        selected,
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
      await widget.controller.announce('Camera ready');
    } on CameraException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.description ?? error.code;
        _initializing = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = 'Camera could not start.';
        _initializing = false;
      });
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
    final camera = _cameraController;

    return Scaffold(
      appBar: AppBar(title: const Text('Camera assistance')),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Container(
                width: double.infinity,
                color: Colors.black,
                alignment: Alignment.center,
                child: _initializing
                    ? const CircularProgressIndicator()
                    : _error != null
                        ? Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              _error!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Colors.white, fontSize: 18),
                            ),
                          )
                        : camera != null && camera.value.isInitialized
                            ? Semantics(
                                image: true,
                                label: 'Live rear camera preview',
                                child: CameraPreview(camera),
                              )
                            : const Text('Camera unavailable', style: TextStyle(color: Colors.white)),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  const Text(
                    'Object inference and encrypted edge streaming are not enabled in this foundation build.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(56)),
                    onPressed: _initializing ? null : _initializeCamera,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Restart camera'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
