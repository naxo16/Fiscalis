import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../data/services/device_identity_service.dart';
import 'infraccion_provider.dart';
import '../../data/datasources/local/database.dart';

enum LoginResult { success, mfaRequired, failure }

final deviceIdentityProvider = Provider<DeviceIdentityService>((ref) {
  return DeviceIdentityService(const FlutterSecureStorage());
});

class AuthNotifier extends StateNotifier<bool> {
  final Dio dio;
  final DeviceIdentityService deviceIdentity;
  AuthNotifier(this.dio, this.deviceIdentity) : super(false);

  final _storage = const FlutterSecureStorage();
  

  Future<LoginResult> login(String rut, String password, {AppDatabase? db}) async {
    if (rut.isEmpty || password.isEmpty) return LoginResult.failure;

    int failedAttempts = 0;
    final failedStr = await _storage.read(key: 'failedAttempts');
    if (failedStr != null) {
      failedAttempts = int.tryParse(failedStr) ?? 0;
    }
    
    if (failedAttempts >= 5) {
      // Bloqueo Criptográfico Temporal (Soft Lock)
      // Permite desbloqueo por Supervisor o continuar la petición para reautenticación síncrona
      // Hash de validación segura
      final storedSupervisorHash = await _storage.read(key: 'supervisor_hash') 
          ?? 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'; // Ejemplo de hash (SHA256 de '123')
      final inputHash = sha256.convert(utf8.encode(password)).toString();

      if (inputHash == storedSupervisorHash) {
        await _storage.write(key: 'failedAttempts', value: '0');
        throw Exception('Desbloqueo de Supervisor exitoso. Por favor, inicie sesión nuevamente.');
      }
      // Si no es la clave de supervisor, dejamos que la petición llegue al backend para autenticación síncrona
    }

    try {
      final deviceId = await deviceIdentity.getDeviceId();
      final response = await dio.post(
        '/api/v1/auth/login',
        data: {
          'username': rut,
          'password': password,
          'device_id': deviceId,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['mfa_required'] == true) {
          await _storage.write(key: 'mfa_token', value: data['mfa_token']);
          return LoginResult.mfaRequired;
        }

        await _saveSession(data);
        return LoginResult.success;
      }
      return LoginResult.failure;
    } catch (e) {
      await _handleLoginError(e, failedAttempts, db);
      return LoginResult.failure;
    }
  }

  Future<bool> verifyMfa(String totpCode, {AppDatabase? db}) async {
    try {
      final mfaToken = await _storage.read(key: 'mfa_token');
      if (mfaToken == null) throw Exception('No hay token MFA pendiente');

      final deviceId = await deviceIdentity.getDeviceId();
      final isRecovery = totpCode.length == 8;
      
      final response = await dio.post(
        '/api/v1/auth/mfa/verify',
        data: {
          'mfa_token': mfaToken,
          'totp_code': isRecovery ? null : totpCode,
          'recovery_code': isRecovery ? totpCode : null,
          'device_id': deviceId,
        },
      );

      if (response.statusCode == 200) {
        await _storage.delete(key: 'mfa_token');
        await _saveSession(response.data);
        return true;
      }
      return false;
    } catch (e) {
            if (e is DioException) {
        final data = e.response?.data;
        String errorMessage = 'Código TOTP inválido o expirado. Intente nuevamente.';
        if (data is Map<String, dynamic> && data.containsKey('detail')) {
          errorMessage = data['detail'];
        }
        throw Exception(errorMessage);
      }
      throw Exception('Error inesperado: ');
    }
  }

  Future<Map<String, dynamic>> setupMfa(String password) async {
    try {
      final jwt = await _storage.read(key: 'jwt');
      if (jwt == null) throw Exception('No hay sesión activa para configurar MFA');

      final response = await dio.post(
        '/api/v1/auth/mfa/setup',
        data: {'password': password},
        options: Options(headers: {'Authorization': 'Bearer $jwt'}),
      );
      
      if (response.statusCode == 200) {
        return response.data; // Retorna otp_auth_url, manual_secret, y recovery_codes
      }
      throw Exception('Fallo al obtener credenciales MFA');
    } catch (e) {
      if (e is DioException) {
        final data = e.response?.data;
        if (data is Map) {
          throw Exception(data['detail'] ?? 'Error de conexión');
        }
        throw Exception(data?.toString() ?? 'Error del servidor: ${e.response?.statusCode}');
      }
      throw Exception('Error inesperado: $e');
    }
  }

  Future<bool> confirmMfa(String totpCode) async {
    try {
      final jwt = await _storage.read(key: 'jwt');
      if (jwt == null) throw Exception('No hay sesión activa para confirmar MFA');

      final response = await dio.post(
        '/api/v1/auth/mfa/confirm',
        data: {'totp_code': totpCode},
        options: Options(headers: {'Authorization': 'Bearer $jwt'}),
      );

      if (response.statusCode == 200) {
        return true;
      }
      return false;
    } catch (e) {
      if (e is DioException) {
        throw Exception(e.response?.data['detail'] ?? 'Código incorrecto. Intente nuevamente.');
      }
      throw Exception('Error inesperado: $e');
    }
  }

  
  Future<bool> revokeMfa(String totpCode) async {
    try {
      final jwt = await _storage.read(key: 'jwt');
      if (jwt == null) throw Exception('No hay sesión activa para revocar MFA');

      final response = await dio.post(
        '/api/v1/auth/mfa/revoke',
        data: {'totp_code': totpCode},
        options: Options(headers: {'Authorization': 'Bearer $jwt'}),
      );

      if (response.statusCode == 200) {
        await _storage.write(key: 'mfa_enabled', value: 'false');
        return true;
      }
      return false;
    } catch (e) {
      if (e is DioException) {
        if (e.response?.statusCode == 400 && e.response?.data['detail'] == 'MFA no esta habilitado') {
          await _storage.write(key: 'mfa_enabled', value: 'false');
          return true; // Handle gracefully if already disabled on backend
        }
        throw Exception(e.response?.data['detail'] ?? 'Código incorrecto.');
      }
      throw Exception('Error inesperado: $e');
    }
  }

  Future<void> _saveSession(dynamic data) async {
    await _storage.write(key: 'jwt', value: data['access_token']);
    final user = data['user'];
    if (user != null) {
      await _storage.write(key: 'inspectorId', value: user['id'].toString());
    }
    await _storage.write(key: 'failedAttempts', value: '0');
    if (mounted) state = true;
  }

  Future<void> _handleLoginError(dynamic e, int failedAttempts, AppDatabase? db) async {
    if (e is DioException) {
      if (e.response?.statusCode == 401) {
        failedAttempts++;
        if (failedAttempts >= 5) {
          await _storage.write(key: 'failedAttempts', value: failedAttempts.toString());
          throw Exception('Bloqueo Temporal (Soft Lock) ACTIVADO: 5 intentos fallidos. Requiere reautenticación síncrona o clave de Supervisor.');
        }
        await _storage.write(key: 'failedAttempts', value: failedAttempts.toString());
        throw Exception('Usuario o contraseña incorrectos. Intento $failedAttempts/5');
      }

      if (e.response?.statusCode == 403) {
        // HARD PURGE: Ejecutado mediante orden remota (Revocado en la tabla maestra)
        await _storage.deleteAll();
        await Future.delayed(const Duration(milliseconds: 200));
        if (db != null) {
          await db.delete(db.actasInfraccion).go();
          await db.delete(db.evidenciasFotograficas).go();
        }
        throw Exception('KILL SWITCH ACTIVADO (Hard Purge): Dispositivo Revocado remótamente. Evidencia destruida por seguridad.');
      }

      if (e.type == DioExceptionType.connectionTimeout || 
          e.type == DioExceptionType.receiveTimeout || 
          e.type == DioExceptionType.sendTimeout) {
        throw Exception('Tiempo de espera agotado al conectar con el backend. Verifique que el servidor esté activo.');
      }

      if (e.type == DioExceptionType.connectionError) {
        throw Exception('No se pudo conectar con el servidor backend. Verifique la URL en Ajustes Técnicos (ícono ⚙️ superior).');
      }

      if (failedAttempts >= 5) {
        throw Exception('Dispositivo en Bloqueo Temporal. Requiere conexión al servidor para reautenticación.');
      }

      final detail = e.response?.data is Map ? e.response?.data['detail'] : null;
      throw Exception(detail ?? 'Error del servidor (HTTP ${e.response?.statusCode ?? 'sin respuesta'})');
    }
    
    if (failedAttempts >= 5) {
       throw Exception('Dispositivo en Bloqueo Temporal. Verifique su conexión para reautenticación síncrona.');
    }
    throw Exception('Error inesperado: $e');
  }

    Future<bool> validateMfa(String code) async {
    try {
      final jwt = await _storage.read(key: 'jwt');
      if (jwt == null) return false;

      final response = await dio.post(
        '/api/v1/auth/mfa/validate',
        data: {'totp_code': code},
        options: Options(headers: {'Authorization': 'Bearer $jwt'}),
      );

      if (response.statusCode == 200) {
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }



  Future<void> checkSessionValidity() async {
    final jwt = await _storage.read(key: 'jwt');
    if (jwt == null) {
      if (mounted) state = false;
      return;
    }

    if (mounted) state = true; // Restaurar sesión

    final now = DateTime.now();

    if (now.hour == 0 && now.minute >= 30) {
      await logout();
      throw Exception('Sesión expirada: Fuera de ventana operacional (>00:30 hrs). Requiere reautenticación.');
    } else if (now.hour > 0 && now.hour < 6) {
      await logout();
      throw Exception('Sesión expirada: Horario no operativo. Requiere reautenticación.');
    }

    final lastSyncStr = await _storage.read(key: 'lastSyncTimestamp');
    if (lastSyncStr != null) {
      final lastSync = DateTime.parse(lastSyncStr);
      final difference = now.difference(lastSync).inHours;
      if (difference >= 72) {
        await logout();
        throw Exception('Aislamiento prolongado crítico (>72 hrs). Bloqueo preventivo. Sincronice y revalide con la institución.');
      }
    } else {
      await _storage.write(key: 'lastSyncTimestamp', value: now.toIso8601String());
    }
  }

  Future<void> logout({AppDatabase? db}) async {
    if (mounted) state = false;
    await _storage.delete(key: 'jwt');
    await _storage.delete(key: 'inspectorId');
    await _storage.delete(key: 'mfa_enabled'); // Borrar estado de MFA para evitar fuga a otra sesión
    if (db != null) {
      // Borrar solo las actas sincronizadas para no perder evidencia (RF-016)
      await (db.delete(db.actasInfraccion)..where((t) => t.estadoActa.equals('SYNCED'))).go();
      // Las fotos en caché asociadas a actas sincronizadas idealmente también se borran,
      // pero para simplificar, borramos el historial local de infracciones completadas.
    }
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, bool>((ref) {
  final dio = ref.watch(dioProvider);
  final deviceIdentity = ref.watch(deviceIdentityProvider);
  return AuthNotifier(dio, deviceIdentity);
});

final mfaStatusProvider = StateNotifierProvider<MfaStatusNotifier, bool>((ref) {
  return MfaStatusNotifier(const FlutterSecureStorage());
});

class MfaStatusNotifier extends StateNotifier<bool> {
  final FlutterSecureStorage _storage;
  MfaStatusNotifier(this._storage) : super(false) {
    _loadStatus();
  }
  Future<void> _loadStatus() async {
    final status = await _storage.read(key: 'mfa_enabled');
    if (mounted) state = status == 'true';
  }
  Future<void> setEnabled(bool isEnabled) async {
    await _storage.write(key: 'mfa_enabled', value: isEnabled ? 'true' : 'false');
    if (mounted) state = isEnabled;
  }
}
