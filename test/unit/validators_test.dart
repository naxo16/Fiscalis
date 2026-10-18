import 'package:flutter_test/flutter_test.dart';
import 'package:sgf_mobile/presentation/utils/validators.dart';

void main() {
  group('AppValidators - Validación de RUT Chileno (Módulo 11)', () {
    test('Acepta RUTs válidos con guión y puntos', () {
      expect(AppValidators.validarRutChileno('11.111.111-1'), isNull);
      expect(AppValidators.validarRutChileno('12.345.678-5'), isNull);
      expect(AppValidators.validarRutChileno('10.000.013-K'), isNull);
    });

    test('Acepta RUTs válidos limpios sin formato', () {
      expect(AppValidators.validarRutChileno('111111111'), isNull);
      expect(AppValidators.validarRutChileno('123456785'), isNull);
      expect(AppValidators.validarRutChileno('10000013k'), isNull);
    });

    test('Rechaza RUTs con dígito verificador incorrecto', () {
      expect(AppValidators.validarRutChileno('11.111.111-2'), isNotNull);
      expect(AppValidators.validarRutChileno('12.345.678-9'), isNotNull);
      expect(AppValidators.validarRutChileno('10.000.013-0'), isNotNull);
    });

    test('Acepta campo vacío o nulo (no obligatorio si conductor no está presente)', () {
      expect(AppValidators.validarRutChileno(null), isNull);
      expect(AppValidators.validarRutChileno(''), isNull);
      expect(AppValidators.validarRutChileno('   '), isNull);
    });

    test('Rechaza strings inválidos de longitud insuficiente', () {
      expect(AppValidators.validarRutChileno('1'), isNotNull);
      expect(AppValidators.validarRutChileno('abc'), isNotNull);
    });
  });

  group('AppValidators - Sanitización OWASP y Anti-Inyección', () {
    test('Remueve caracteres peligrosos (<, >, ;)', () {
      const maliciousInput = '<script>alert("xss");</script>; DROP TABLE actas;';
      final sanitized = AppValidators.sanitizeText(maliciousInput);
      expect(sanitized.contains('<'), isFalse);
      expect(sanitized.contains('>'), isFalse);
      expect(sanitized.contains(';'), isFalse);
    });

    test('Conserva texto legal válido sin alterarlo innecesariamente', () {
      const validText = 'Vehículo estacionado sobre la acera frente al número 1240.';
      expect(AppValidators.sanitizeText(validText), equals(validText));
    });
  });
}
