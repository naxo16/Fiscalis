import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../data/datasources/local/database.dart';
import '../../data/repositories/infraccion_repository_impl.dart';
import '../../domain/repositories/i_infraccion_repository.dart';
import '../../data/services/sync_service.dart';
import '../../domain/entities/infraccion.dart'; // Importante para que reconozca el tipo
import 'settings_provider.dart';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../data/services/device_identity_service.dart';
// 1. Proveedor de la base de datos (Singleton)
final databaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(() => db.close());
  return db;
});

// 2. Proveedor de Dio
final dioProvider = Provider<Dio>((ref) {
  final baseUrl = ref.watch(serverUrlProvider);
  final dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
    sendTimeout: const Duration(seconds: 30),
  ));
  
  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      const storage = FlutterSecureStorage();
      final token = await storage.read(key: 'jwt');
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      
      // Adjuntamos X-Device-Id de forma global
      final deviceService = DeviceIdentityService(storage);
      final deviceId = await deviceService.getDeviceId();
      options.headers['X-Device-Id'] = deviceId;
      
      return handler.next(options);
    },
    onError: (DioException e, handler) async {
      // Manejo global de 401/403 se realiza en AuthNotifier o en interceptor específico.
      // Para mantenerlo limpio, AuthNotifier atrapa los login errors.
      // Aquí podríamos limpiar storage para 401, pero AuthNotifier lo maneja.
      return handler.next(e);
    }
  ));

  return dio;
});

// 3. Proveedor del repositorio (Repository)
final infraccionRepositoryProvider = Provider<IInfraccionRepository>((ref) {
  final db = ref.watch(databaseProvider);
  final dio = ref.watch(dioProvider); // Usamos la instancia configurada arriba
  return InfraccionRepositoryImpl(db, dio);
});

// 4. Proveedor reactivo para el Historial (¡Aquí corregí el 'List >' por 'List<Infraccion>'!)
final infraccionesStreamProvider = StreamProvider<List<Infraccion>>((ref) {
  final repository = ref.watch(infraccionRepositoryProvider);
  return repository.watchInfracciones();
});

// 5. Proveedor de Sincronización
final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(databaseProvider); 
  final dio = ref.watch(dioProvider);
  return SyncService(db: db, dio: dio);
});

// 6. Proveedor reactivo de cantidad de actas pendientes de sincronización
final pendingInfraccionesCountProvider = StreamProvider<int>((ref) {
  final db = ref.watch(databaseProvider);
  return (db.select(db.actasInfraccion)..where((t) => t.estadoActa.equals('PENDIENTE_SYNC')))
      .watch()
      .map((rows) => rows.length);
});