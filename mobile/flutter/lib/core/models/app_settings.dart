class AppSettings {
  const AppSettings({
    this.languageCode = 'en-US',
    this.speechEnabled = true,
    this.vibrationEnabled = true,
    this.edgeHost = '192.168.4.2',
    this.edgePort = 9999,
  });

  final String languageCode;
  final bool speechEnabled;
  final bool vibrationEnabled;
  final String edgeHost;
  final int edgePort;

  AppSettings copyWith({
    String? languageCode,
    bool? speechEnabled,
    bool? vibrationEnabled,
    String? edgeHost,
    int? edgePort,
  }) {
    return AppSettings(
      languageCode: languageCode ?? this.languageCode,
      speechEnabled: speechEnabled ?? this.speechEnabled,
      vibrationEnabled: vibrationEnabled ?? this.vibrationEnabled,
      edgeHost: edgeHost ?? this.edgeHost,
      edgePort: edgePort ?? this.edgePort,
    );
  }
}
