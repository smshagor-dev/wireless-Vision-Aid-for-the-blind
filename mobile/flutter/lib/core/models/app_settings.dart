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

const legacyDetectedClassesV1 = <String>{
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
};

const allCocoDetectedClasses = <String>{
  'person',
  'bicycle',
  'car',
  'motorcycle',
  'airplane',
  'bus',
  'train',
  'truck',
  'boat',
  'traffic light',
  'fire hydrant',
  'stop sign',
  'parking meter',
  'bench',
  'bird',
  'cat',
  'dog',
  'horse',
  'sheep',
  'cow',
  'elephant',
  'bear',
  'zebra',
  'giraffe',
  'backpack',
  'umbrella',
  'handbag',
  'tie',
  'suitcase',
  'frisbee',
  'skis',
  'snowboard',
  'sports ball',
  'kite',
  'baseball bat',
  'baseball glove',
  'skateboard',
  'surfboard',
  'tennis racket',
  'bottle',
  'wine glass',
  'cup',
  'fork',
  'knife',
  'spoon',
  'bowl',
  'banana',
  'apple',
  'sandwich',
  'orange',
  'broccoli',
  'carrot',
  'hot dog',
  'pizza',
  'donut',
  'cake',
  'chair',
  'couch',
  'potted plant',
  'bed',
  'dining table',
  'toilet',
  'tv',
  'laptop',
  'mouse',
  'remote',
  'keyboard',
  'cell phone',
  'microwave',
  'oven',
  'toaster',
  'sink',
  'refrigerator',
  'book',
  'clock',
  'vase',
  'scissors',
  'teddy bear',
  'hair drier',
  'toothbrush',
};

class AppSettings {
  const AppSettings({
    this.firstRunCompleted = false,
    this.userName = '',
    this.languageCode = 'en-US',
    this.cameraSource = CameraSourceType.phone,
    this.speechEnabled = true,
    this.vibrationEnabled = true,
    this.esp32ListenPort = 9999,
    this.autoReconnect = true,
    this.detectionConfidence = 0.25,
    this.detectedClasses = allCocoDetectedClasses,
  });

  final bool firstRunCompleted;
  final String userName;
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
    String? userName,
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
      userName: userName ?? this.userName,
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
