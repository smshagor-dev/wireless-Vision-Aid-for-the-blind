enum EdgeConfigurationState { unconfigured, configured }

class EdgeEndpoint {
  const EdgeEndpoint({required this.host, required this.port});

  final String host;
  final int port;

  @override
  String toString() => '$host:$port';
}

class EdgeConnectionService {
  EdgeEndpoint? _endpoint;

  EdgeEndpoint? get endpoint => _endpoint;

  EdgeConfigurationState get state => _endpoint == null
      ? EdgeConfigurationState.unconfigured
      : EdgeConfigurationState.configured;

  void configure({required String host, required int port}) {
    final normalizedHost = host.trim();
    if (normalizedHost.isEmpty || normalizedHost.length > 253) {
      throw const FormatException('Enter a valid edge-server host.');
    }
    if (normalizedHost.contains(RegExp(r'\s'))) {
      throw const FormatException('Edge-server host cannot contain spaces.');
    }
    if (port < 1 || port > 65535) {
      throw const FormatException('Port must be between 1 and 65535.');
    }

    _endpoint = EdgeEndpoint(host: normalizedHost, port: port);
  }

  void clear() {
    _endpoint = null;
  }
}
