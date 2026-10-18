import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sgf_mobile/main.dart';
import 'package:sgf_mobile/presentation/pages/splash_screen.dart';

void main() {
  testWidgets('Smoke test: Inicialización y renderizado de SplashScreen', (WidgetTester tester) async {
    // Montamos la aplicación con ProviderScope
    await tester.pumpWidget(
      const ProviderScope(
        child: MyApp(),
      ),
    );

    // Verificamos que la aplicación arranca en el SplashScreen
    expect(find.byType(SplashScreen), findsOneWidget);

    // Verificamos que renderiza el título institucional 'FISCALIS' y su subtitulo
    expect(find.text('FISCALIS'), findsOneWidget);
    expect(find.text('Sistema de Gestión Operativa'), findsOneWidget);

    // Avanzamos el timer
    await tester.pump(const Duration(seconds: 1));
  });
}
