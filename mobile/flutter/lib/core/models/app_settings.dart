class AppSettings {
  const AppSettings({
    this.languageCode = 'en-US',
    this.speechEnabled = true,
    this.vibrationEnabled = true,
    this.edgeHost = '192.168.4.2',
    this.edgePort = 9999,
    this.edgeMode = true,
    this.autoReconnect = true,
    this.detectionConfidence = 0.50,
    this.detectedClasses = const {
      'person',
      'vehicle',
      'bicycle',
      'motorcycle',
      'obstacle',
      'stairs',
      'curb',
    },
  });

  final String languageCode;
  final bool speechEnabled;
  final bool vibrationEnabled;
  final String edgeHost;
  final int edgePort;
  final bool edgeMode;
  final bool autoReconnect;
  final double detectionConfidence;
  final Set<String> detectedClasses;

  AppSettings copyWith({
    String? languageCode,
    bool? speechEnabled,
    bool? vibrationEnabled,
    String? edgeHost,
    int? edgePort,
    bool? edgeMode,
    bool? autoReconnect,
    double? detectionConfidence,
    Set<String>? detectedClasses,
  }) {
    return AppSettings(
      languageCode: languageCode ?? this.languageCode,
      speechEnabled: speechEnabled ?? this.speechEnabled,
      vibrationEnabled: vibrationEnabled ?? this.vibrationEnabled,
      edgeHost: edgeHost ?? this.edgeHost,
      edgePort: edgePort ?? this.edgePort,
      edgeMode: edgeMode ?? this.edgeMode,
      autoReconnect: autoReconnect ?? this.autoReconnect,
      detectionConfidence: detectionConfidence ?? this.detectionConfidence,
      detectedClasses: detectedClasses ?? this.detectedClasses,
    );
  }
}
