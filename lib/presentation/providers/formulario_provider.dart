import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';
import 'package:drift/drift.dart'; // REQUIRED FOR Value
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../data/datasources/local/database.dart';
import 'infraccion_provider.dart';

class EvidenciaFotoItem {
  final String path;
  final String hash;
  final Uint8List? bytes;

  const EvidenciaFotoItem({
    required this.path,
    required this.hash,
    this.bytes,
  });

  Map<String, String> toLegacyMap() {
    return {'path': path, 'hash': hash};
  }
}

class FormularioState {
  final double? latitud;
  final double? longitud;
  final List<EvidenciaFotoItem> evidencias;
  final bool isLoading;
  final String? feedbackMessage;
  final bool isUbicacionManual;

  FormularioState({
    this.latitud,
    this.longitud,
    this.evidencias = const [],
    this.isLoading = false,
    this.feedbackMessage,
    this.isUbicacionManual = false,
  });

  // Backward-compatible getter for legacy callers
  List<Map<String, String>> get fotosConHash => 
      evidencias.map((e) => e.toLegacyMap()).toList();

  FormularioState copyWith({
    double? latitud,
    double? longitud,
    List<EvidenciaFotoItem>? evidencias,
    bool? isLoading,
    String? feedbackMessage,
    bool? isUbicacionManual,
  }) {
    return FormularioState(
      latitud: latitud ?? this.latitud,
      longitud: longitud ?? this.longitud,
      evidencias: evidencias ?? this.evidencias,
      isLoading: isLoading ?? this.isLoading,
      feedbackMessage: feedbackMessage,
      isUbicacionManual: isUbicacionManual ?? this.isUbicacionManual,
    );
  }
}

class FormularioInfraccionNotifier extends StateNotifier<FormularioState> {
  final AppDatabase _db;
  final ImagePicker _picker = ImagePicker();
  final _storage = const FlutterSecureStorage();
  int _inspectorId = 101; // Inspector ID por defecto (fallback)

  // Coordenadas céntricas institucionales de Cauquenes como fallback
  static const double kDefaultLatCauquenes = -35.9664;
  static const double kDefaultLngCauquenes = -72.3114;

  FormularioInfraccionNotifier(this._db) : super(FormularioState()) {
    _initInspectorId();
  }

  Future<void> _initInspectorId() async {
    try {
      final idStr = await _storage.read(key: 'inspectorId');
      if (idStr != null) {
        _inspectorId = int.tryParse(idStr) ?? 101;
      }
    } catch (_) {
      // Fallback por defecto 101
    }
  }

  void setCoordenadasManuales(double lat, double lng) {
    state = state.copyWith(
      latitud: lat,
      longitud: lng,
      isUbicacionManual: true,
      feedbackMessage: 'Coordenadas manuales establecidas',
    );
  }

  Future<void> capturarGPS() async {
    state = state.copyWith(isLoading: true, feedbackMessage: null);
    try {
      bool serviceEnabled = false;
      try {
        serviceEnabled = await Geolocator.isLocationServiceEnabled();
      } catch (_) {
        // En navegadores o entornos sin soporte de sensor
        serviceEnabled = false;
      }

      if (!serviceEnabled) {
        _aplicarFallbackCoordenadas('Sensor GPS no disponible. Aplicada ubicación municipal.');
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          _aplicarFallbackCoordenadas('Permiso de GPS denegado. Se asignó ubicación institucional.');
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        _aplicarFallbackCoordenadas('Permiso de GPS bloqueado permanentemente. Ubicación referencial.');
        return;
      }

      Position? position;
      try {
        // Intentar obtener con timeout para que nunca se quede colgado
        position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.medium,
            timeLimit: Duration(seconds: 6),
          ),
        );
      } catch (_) {
        // Si hay timeout o error de sensor, intentar última conocida
        position = await Geolocator.getLastKnownPosition();
      }

      if (position != null) {
        state = state.copyWith(
          latitud: position.latitude,
          longitud: position.longitude,
          isLoading: false,
          isUbicacionManual: false,
          feedbackMessage: 'Ubicación GPS obtenida con éxito (${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)})',
        );
      } else {
        _aplicarFallbackCoordenadas('Sin señal satelital inmediata. Se asignó ubicación municipal.');
      }
    } catch (e) {
      _aplicarFallbackCoordenadas('Ubicación referencial asignada (Modo contingencia).');
    }
  }

  void _aplicarFallbackCoordenadas(String mensaje) {
    state = state.copyWith(
      latitud: kDefaultLatCauquenes,
      longitud: kDefaultLngCauquenes,
      isLoading: false,
      isUbicacionManual: true,
      feedbackMessage: mensaje,
    );
  }

  Future<bool> tomarFotografia({ImageSource source = ImageSource.camera}) async {
    state = state.copyWith(feedbackMessage: null);
    try {
      final XFile? photo = await _picker.pickImage(
        source: source,
        imageQuality: 55,
        maxWidth: 1280,
        maxHeight: 1280,
      );
      if (photo == null) return false;

      // Leer bytes siempre compatible con Web, Desktop y Móvil
      final Uint8List bytes = await photo.readAsBytes();
      final String hash = sha256.convert(bytes).toString();

      String finalPath;
      if (kIsWeb) {
        finalPath = 'web_blob_${const Uuid().v4()}.jpg';
      } else {
        try {
          final Directory appDocDir = await getApplicationDocumentsDirectory();
          final String fileName = '${const Uuid().v4()}.jpg';
          finalPath = '${appDocDir.path}/$fileName';
          await File(finalPath).writeAsBytes(bytes);
        } catch (_) {
          finalPath = photo.path;
        }
      }

      final nuevoItem = EvidenciaFotoItem(
        path: finalPath,
        hash: hash,
        bytes: bytes,
      );

      state = state.copyWith(
        evidencias: [...state.evidencias, nuevoItem],
        feedbackMessage: 'Fotografía adjuntada con éxito (Hash: ${hash.substring(0, 8)})',
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        feedbackMessage: 'No se pudo capturar la imagen. Intente desde galería/archivos.',
      );
      return false;
    }
  }

  Future<void> recuperarFotoPerdida() async {
    if (kIsWeb) return;
    try {
      if (Platform.isAndroid) {
        final LostDataResponse response = await _picker.retrieveLostData();
        if (response.isEmpty || response.file == null) return;

        final bytes = await response.file!.readAsBytes();
        final hash = sha256.convert(bytes).toString();

        final Directory appDocDir = await getApplicationDocumentsDirectory();
        final String fileName = '${const Uuid().v4()}.jpg';
        final String permanentPath = '${appDocDir.path}/$fileName';
        await File(permanentPath).writeAsBytes(bytes);

        final nuevoItem = EvidenciaFotoItem(
          path: permanentPath,
          hash: hash,
          bytes: bytes,
        );

        state = state.copyWith(
          evidencias: [...state.evidencias, nuevoItem],
        );
      }
    } catch (_) {}
  }

  void eliminarFotografia(String path) {
    final newEvidencias = state.evidencias.where((f) => f.path != path).toList();
    state = state.copyWith(evidencias: newEvidencias);

    if (!kIsWeb) {
      try {
        final file = File(path);
        if (file.existsSync()) {
          file.deleteSync();
        }
      } catch (_) {}
    }
  }

  Future<void> guardarActa({
    required String ppu,
    required String tipoVehiculo,
    required String colorVehiculo,
    required String marcaVehiculo,
    required String observaciones,
    String? nombreInfractor, // <-- NUEVO
    String? rutInfractor,    // <-- NUEVO
    int? tipoInfraccionId,   // <-- NUEVO (1 = Advertencia, 2 = Citación)
    bool firmaRechazo = false,
  }) async {
    final actaUuid = const Uuid().v4();
    
    await _db.transaction(() async {
      await _db.into(_db.actasInfraccion).insert(
        ActasInfraccionCompanion.insert(
          uuid: actaUuid,
          latitud: state.latitud ?? 0.0,
          longitud: state.longitud ?? 0.0,
          ppu: ppu,
          nombreInfractor: Value(nombreInfractor), 
          rutInfractor: Value(rutInfractor),       
          tipoVehiculo: tipoVehiculo,
          colorVehiculo: colorVehiculo,
          marcaVehiculo: marcaVehiculo,
          tipoInfraccionId: tipoInfraccionId ?? 1, 
          observaciones: observaciones,
          inspectorId: _inspectorId, 
          estadoActa: 'PENDIENTE_SYNC',
          deviceId: 'MOCK_DEVICE_ID',
          firmaRechazo: Value(firmaRechazo),
        ),
      );

      for (var foto in state.fotosConHash) {
        await _db.into(_db.evidenciasFotograficas).insert(
          EvidenciasFotograficasCompanion.insert(
            id: const Uuid().v4(),
            actaUuid: actaUuid,
            rutaLocal: foto['path']!,
            hashIntegridad: foto['hash']!,
          ),
        );
      }
    });

    state = FormularioState(); // Reset
  }
}

final formularioInfraccionProvider = StateNotifierProvider<FormularioInfraccionNotifier, FormularioState>((ref) {
  return FormularioInfraccionNotifier(ref.watch(databaseProvider));
});