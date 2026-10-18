import 'package:flutter_test/flutter_test.dart';
import 'package:sgf_mobile/presentation/utils/formatters.dart';

void main() {
  group('Formatters - RutFormatter', () {
    final formatter = RutFormatter();

    test('Formatea números crudos a formato RUT con puntos y guión', () {
      const oldValue = TextEditingValue.empty;
      const newValue = TextEditingValue(text: '123456785');
      final result = formatter.formatEditUpdate(oldValue, newValue);
      expect(result.text, equals('12.345.678-5'));
    });

    test('Maneja dígito verificador K mayúscula o minúscula', () {
      const oldValue = TextEditingValue.empty;
      const newValue = TextEditingValue(text: '11111111k');
      final result = formatter.formatEditUpdate(oldValue, newValue);
      expect(result.text, equals('11.111.111-K'));
    });

    test('Retorna vacío si el input está vacío', () {
      const oldValue = TextEditingValue.empty;
      const newValue = TextEditingValue(text: '');
      final result = formatter.formatEditUpdate(oldValue, newValue);
      expect(result.text, equals(''));
    });
  });

  group('Formatters - PpuFormatter (Patente Vehicular Chilena)', () {
    final formatter = PpuFormatter();

    test('Formatea patente de 6 caracteres con guión separador y mayúsculas', () {
      const oldValue = TextEditingValue.empty;
      const newValue = TextEditingValue(text: 'kkyz88');
      final result = formatter.formatEditUpdate(oldValue, newValue);
      expect(result.text, equals('KKYZ-88'));
    });

    test('Limita la patente a un máximo de 6 caracteres alfanuméricos', () {
      const oldValue = TextEditingValue.empty;
      const newValue = TextEditingValue(text: 'abcd12345extra');
      final result = formatter.formatEditUpdate(oldValue, newValue);
      expect(result.text, equals('ABCD-12'));
    });
  });
}
