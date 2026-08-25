enum CameraSourceType { phone, esp32 }

CameraSourceType cameraSourceFromStorage(String? value) {
  return switch (value) {
    'esp32' => CameraSourceType.esp32,
    _ => CameraSourceType.phone,
  };
}

extension CameraSourceTypeStorage on CameraSourceType {
  String get storageValue => this == CameraSourceType.esp32 ? 'esp32' : 'phone';
}

class AppSettings {
  const AppSettings({
    this.firstRunCompleted = false,
    this.languageCode = 'en-US',
    this.cameraSource = CameraSourceType.phone,
    this.speechEnabled = true,
    this.vibrationEnabled = true,
    this.esp32ListenPort = 9999,
    this.autoReconnect = true,
    this.detectionConfidence = 0.50,
    this.detectedClasses = const {
      'person',
      'car',
      'truck',
      'bus',
      'bicycle',
      'motorcycle',
      'traffic light',
      'stop sign',
      'chair',
      'bench',
      'potted plant',
    },
  });

  final bool firstRunCompleted;
  final String languageCode;
  final CameraSourceType cameraSource;
  final bool speechEnabled;
  final bool vibrationEnabled;
  final int esp32ListenPort;
  final bool autoReconnect;
  final double detectionConfidence;
  final Set<String> detectedClasses;

  AppSettings copyWith({
    bool? firstRunCompleted,
    String? languageCode,
    CameraSourceType? cameraSource,
    bool? speechEnabled,
    bool? vibrationEnabled,
    int? esp32ListenPort,
    bool? autoReconnect,
    double? detectionConfidence,
    Set<String>? detectedClasses,
  }) {
    return AppSettings(
      firstRunCompleted: firstRunCompleted ?? this.firstRunCompleted,
      languageCode: languageCode ?? this.languageCode,
      cameraSource: cameraSource ?? this.cameraSource,
      speechEnabled: speechEnabled ?? this.speechEnabled,
      vibrationEnabled: vibrationEnabled ?? this.vibrationEnabled,
      esp32ListenPort: esp32ListenPort ?? this.esp32ListenPort,
      autoReconnect: autoReconnect ?? this.autoReconnect,
      detectionConfidence: detectionConfidence ?? this.detectionConfidence,
      detectedClasses: detectedClasses ?? this.detectedClasses,
    );
  }
}
