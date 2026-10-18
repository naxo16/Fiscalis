import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../providers/settings_provider.dart';
import '../providers/infraccion_provider.dart';
import '../utils/formatters.dart';
import '../utils/validators.dart';

/// Pantalla de acceso para Inspectores de Seguridad Pública.
/// Implementa la identidad visual 'Fiscalis' con la paleta corporativa de Cauquenes.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _rutController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _rutController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final currentUrl = ref.read(serverUrlProvider);
    final isMobileDevice = !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS);
    if (currentUrl.isEmpty || (isMobileDevice && currentUrl.contains('localhost'))) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('En móvil o emulador, configure la IP de su PC o 10.0.2.2 en Ajustes')),
      );
      return;
    }

    if (_rutController.text.isEmpty || _passwordController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, complete todos los campos')),
      );
      return;
    }

    final rutError = AppValidators.validarRutChileno(_rutController.text);
    if (rutError != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(rutError)),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final cleanRut = _rutController.text.replaceAll('.', '').trim();
      final cleanPassword = _passwordController.text.trim();

      final db = ref.read(databaseProvider);
      final result = await ref.read(authProvider.notifier).login(cleanRut, cleanPassword, db: db);

      if (mounted) {
        setState(() => _isLoading = false);
        if (result == LoginResult.success) {
          Navigator.pushReplacementNamed(context, '/home');
        } else if (result == LoginResult.mfaRequired) {
          Navigator.pushReplacementNamed(context, '/mfa_verify');
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Credenciales incorrectas')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceAll('Exception: ', ''))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings, color: Color(0xFF171557)),
            tooltip: 'Ajustes Técnicos',
            onPressed: () => Navigator.pushNamed(context, '/ajustes'),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(height: 32),
                  // Header Institucional
                  Image.asset(
                    'assets/images/fiscalis_logo.png',
                    height: 120,
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'FISCALIS',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 4,
                      color: Color(0xFF171557),
                    ),
                  ),
                  const SizedBox(height: 48),
                  
                  // Formulario de Acceso
                  _buildTextField(
                    controller: _rutController,
                    label: 'RUT del Inspector',
                    icon: Icons.badge_outlined,
                    inputFormatters: [OwaspSanitizerFormatter(12), RutFormatter()],
                  ),
                  const SizedBox(height: 16),
                  _buildTextField(
                    controller: _passwordController,
                    label: 'Contraseña',
                    icon: Icons.lock_outline,
                    isPassword: true,
                    inputFormatters: [OwaspSanitizerFormatter(64)],
                  ),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () => Navigator.pushNamed(context, '/ajustes'),
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 8.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.cloud_outlined, size: 14, color: Colors.black45),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              'Servidor: ${ref.watch(serverUrlProvider)}',
                              style: const TextStyle(fontSize: 12, color: Colors.black54),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.edit, size: 12, color: Colors.black38),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  
                  // Botón de Acción
                  SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _handleLogin,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF171557),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              height: 24,
                              width: 24,
                              child: CircularProgressIndicator(
                                color: Colors.white,
                                strokeWidth: 2,
                              ),
                            )
                          : const Text(
                              'Ingresar',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 48),
                  
                  // Footer / Marca de Agua
                  const Padding(
                    padding: EdgeInsets.only(bottom: 16.0),
                    child: Text(
                      'Fiscalis v1.0.0 • Desarrollado por Renkai',
                      style: TextStyle(
                        color: Colors.black38,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool isPassword = false,
    List<TextInputFormatter>? inputFormatters,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: isPassword,
      inputFormatters: inputFormatters,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, color: const Color(0xFF171557)),
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF171557), width: 2),
        ),
      ),
    );
  }
}
