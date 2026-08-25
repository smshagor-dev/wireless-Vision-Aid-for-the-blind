import 'package:flutter_test/flutter_test.dart';
import 'package:wvab_mobile/core/services/edge_connection_service.dart';

void main() {
  test('configures a validated edge endpoint without claiming connection', () {
    final service = EdgeConnectionService();

    service.configure(host: '192.168.4.2', port: 9999);

    expect(service.state, EdgeConfigurationState.configured);
    expect(service.endpoint.toString(), '192.168.4.2:9999');
  });

  test('rejects invalid host and port', () {
    final service = EdgeConnectionService();

    expect(() => service.configure(host: 'bad host', port: 9999), throwsFormatException);
    expect(() => service.configure(host: '127.0.0.1', port: 70000), throwsFormatException);
  });
}
