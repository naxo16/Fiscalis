import 'package:flutter_test/flutter_test.dart';
import 'package:sgf_mobile/data/models/infraccion_model.dart';
import 'package:sgf_mobile/domain/entities/infraccion.dart';

void main() {
  group('InfraccionModel & Domain Entity Tests', () {
    final now = DateTime.now();

    final model = InfraccionModel(
      id: '550e8400-e29b-41d4-a716-446655440000',
      rutInfractor: '11.111.111-1',
      nombreCompleto: 'Juan Test',
      ppu: 'KKYZ-88',
      tipoVehiculo: 'Camioneta',
      marcaVehiculo: 'Toyota',
      colorVehiculo: 'Blanco',
      tipoInfraccionId: 1,
      coordenadas: '-35.9664,-72.3114',
      fotos: const ['hash_sha256_mock_1', 'hash_sha256_mock_2'],
      fecha: now,
      descripcion: 'Estacionado en lugar prohibido',
      firmaRechazo: false,
      status: InfraccionStatus.guardadoLocal,
    );

    test('toJson() produce un mapa compatible con el contrato de FastAPI backend', () {
      final json = model.toJson();

      expect(json['id'], equals('550e8400-e29b-41d4-a716-446655440000'));
      expect(json['rutInfractor'], equals('11.111.111-1'));
      expect(json['nombreCompleto'], equals('Juan Test'));
      expect(json['ppu'], equals('KKYZ-88'));
      expect(json['tipoVehiculo'], equals('Camioneta'));
      expect(json['marcaVehiculo'], equals('Toyota'));
      expect(json['colorVehiculo'], equals('Blanco'));
      expect(json['tipoInfraccionId'], equals(1));
      expect(json['coordenadas'], equals('-35.9664,-72.3114'));
      expect(json['fotos'], hasLength(2));
      expect(json['fecha'], equals(now.toIso8601String()));
      expect(json['descripcion'], equals('Estacionado en lugar prohibido'));
      expect(json['firmaRechazo'], isFalse);
      expect(json['status'], equals('guardadoLocal'));
    });

    test('InfraccionModel hereda de la entidad de dominio Infraccion', () {
      expect(model, isA<Infraccion>());
      expect(model.id, equals('550e8400-e29b-41d4-a716-446655440000'));
      expect(model.ppu, equals('KKYZ-88'));
    });
  });
}
