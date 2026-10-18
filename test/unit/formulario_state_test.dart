import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sgf_mobile/presentation/providers/formulario_provider.dart';

void main() {
  group('EvidenciaFotoItem & FormularioState Tests', () {
    test('EvidenciaFotoItem retiene bytes en memoria y mapea hash/path correctamente', () {
      final dummyBytes = Uint8List.fromList([1, 2, 3, 4, 5, 255]);
      const dummyHash = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
      const dummyPath = 'test/path/foto.jpg';

      final item = EvidenciaFotoItem(
        path: dummyPath,
        hash: dummyHash,
        bytes: dummyBytes,
      );

      expect(item.path, equals(dummyPath));
      expect(item.hash, equals(dummyHash));
      expect(item.bytes, isNotNull);
      expect(item.bytes!.length, equals(6));

      // Comprobación de compatibilidad hacia atrás
      final legacyMap = item.toLegacyMap();
      expect(legacyMap['path'], equals(dummyPath));
      expect(legacyMap['hash'], equals(dummyHash));
    });

    test('FormularioState inicializa con lista vacía de evidencias y coordenadas nulas', () {
      final state = FormularioState();

      expect(state.latitud, isNull);
      expect(state.longitud, isNull);
      expect(state.evidencias, isEmpty);
      expect(state.fotosConHash, isEmpty);
      expect(state.isLoading, isFalse);
      expect(state.isUbicacionManual, isFalse);
      expect(state.feedbackMessage, isNull);
    });

    test('FormularioState copyWith preserva estados y actualiza coordenadas y evidencias', () {
      final state = FormularioState();
      const testLat = -35.9664;
      const testLng = -72.3114;
      final dummyItem = EvidenciaFotoItem(
        path: 'img_test.jpg',
        hash: 'abcd1234abcd5678',
        bytes: Uint8List.fromList([10, 20]),
      );

      final updatedState = state.copyWith(
        latitud: testLat,
        longitud: testLng,
        evidencias: [dummyItem],
        isUbicacionManual: true,
        feedbackMessage: 'Ubicación municipal de contingencia asignada',
      );

      expect(updatedState.latitud, equals(testLat));
      expect(updatedState.longitud, equals(testLng));
      expect(updatedState.isUbicacionManual, isTrue);
      expect(updatedState.evidencias.length, equals(1));
      expect(updatedState.fotosConHash.first['path'], equals('img_test.jpg'));
      expect(updatedState.feedbackMessage, contains('Ubicación municipal'));
    });

    test('Valores de contingencia por defecto de Cauquenes están configurados correctamente', () {
      expect(FormularioInfraccionNotifier.kDefaultLatCauquenes, closeTo(-35.9664, 0.001));
      expect(FormularioInfraccionNotifier.kDefaultLngCauquenes, closeTo(-72.3114, 0.001));
    });
  });
}
