import '../../domain/entities/infraccion.dart';
import '../datasources/local/database.dart';

class InfraccionModel extends Infraccion {
  const InfraccionModel({
    required super.id,
    super.rutInfractor,
    super.nombreCompleto,
    required super.ppu,
    super.tipoVehiculo,
    super.marcaVehiculo,
    super.colorVehiculo,
    super.tipoInfraccionId,
    required super.coordenadas,
    required super.fotos,
    required super.fecha,
    required super.descripcion,
    super.firmaRechazo,
    required super.status,
  });

  factory InfraccionModel.fromEntity(Infraccion entity) {
    return InfraccionModel(
      id: entity.id,
      rutInfractor: entity.rutInfractor,
      nombreCompleto: entity.nombreCompleto,
      ppu: entity.ppu,
      tipoVehiculo: entity.tipoVehiculo,
      marcaVehiculo: entity.marcaVehiculo,
      colorVehiculo: entity.colorVehiculo,
      tipoInfraccionId: entity.tipoInfraccionId,
      coordenadas: entity.coordenadas,
      fotos: entity.fotos,
      fecha: entity.fecha,
      descripcion: entity.descripcion,
      firmaRechazo: entity.firmaRechazo,
      status: entity.status,
    );
  }

  // Factory adaptado a la nueva base de datos DERA (ActasInfraccion)
  factory InfraccionModel.fromDatabase(ActasInfraccionData row, {List<String> fotos = const []}) {
    return InfraccionModel(
      id: row.uuid,
      rutInfractor: row.rutInfractor,
      nombreCompleto: row.nombreInfractor,
      ppu: row.ppu,
      tipoVehiculo: row.tipoVehiculo,
      marcaVehiculo: row.marcaVehiculo,
      colorVehiculo: row.colorVehiculo,
      tipoInfraccionId: row.tipoInfraccionId,
      coordenadas: '${row.latitud},${row.longitud}',
      fotos: fotos,
      fecha: row.createdAt,
      descripcion: row.observaciones,
      firmaRechazo: row.firmaRechazo,
      status: row.estadoActa == 'SYNCED' 
          ? InfraccionStatus.sincronizado 
          : InfraccionStatus.guardadoLocal,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'rutInfractor': rutInfractor,
      'nombreCompleto': nombreCompleto,
      'ppu': ppu,
      'tipoVehiculo': tipoVehiculo,
      'marcaVehiculo': marcaVehiculo,
      'colorVehiculo': colorVehiculo,
      'tipoInfraccionId': tipoInfraccionId,
      'coordenadas': coordenadas,
      'fotos': fotos,
      'fecha': fecha.toIso8601String(),
      'descripcion': descripcion,
      'firmaRechazo': firmaRechazo,
      'status': status.name,
    };
  }
}