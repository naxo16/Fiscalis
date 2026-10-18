# FISCALIS (SGF Mobile) - Aplicación Operativa de Fiscalización Municipal

Aplicación móvil y web progresiva (PWA) de alta resiliencia diseñada para inspectores municipales en terreno, construida con **Flutter** y **Riverpod**. Opera bajo el paradigma **Offline-First**, permitiendo cursar actas de infracción vehicular y capturar evidencia georreferenciada sin depender de conectividad satelital o de red en tiempo real.

---

## 🚀 Características Principales

- **Arquitectura Offline-First:** Persistencia local reactiva con base de datos SQLite / Drift cifrada.
- **Evidencia Fotográfica Multiplataforma:** Captura de fotos desde cámara nativa o galería/archivos con procesamiento de bytes en memoria (`Uint8List`) y hash criptográfico SHA-256 en cliente para cadena de custodia.
- **Geolocalización Resiliente:** Detección asistida por GPS con timeout preventivo de 6 segundos y fallback inmediato a coordenadas municipales institucionales (Cauquenes: `-35.9664, -72.3114`) o afinamiento manual.
- **Autenticación Robusta:** JWT Stateless con soporte para segundo factor MFA (TOTP RFC 6238) y pantalla de bloqueo por inactividad (`SessionLockScreen`).
- **Validaciones Legales Chilenas:** Módulo 11 para RUT de infractores y formateadores de Patente Única Vehicular (PPU).

---

## 🏗️ Estructura del Proyecto

```
sgf_mobile/
├── lib/
│   ├── data/
│   │   ├── datasources/local/   # Drift / SQLite Database (Tablas, DAOs, cifrado)
│   │   ├── models/              # Modelos de datos y mapeos JSON
│   │   └── services/            # Servicios de sincronización (Dio) y ubicación
│   ├── domain/
│   │   └── entities/            # Entidades de dominio puro
│   ├── presentation/
│   │   ├── pages/               # Pantallas (Login, MFA, Formulario, Historial)
│   │   ├── providers/           # Gestores de estado (Riverpod StateNotifiers)
│   │   ├── utils/               # Validadores (Módulo 11, OWASP) y Formatters
│   │   └── widgets/             # Componentes reusables y scaffolding
│   └── main.dart                # Punto de entrada de la aplicación
├── test/
│   ├── unit/                    # Pruebas unitarias (RUT, PPU, FormularioState, Models)
│   └── widget_test.dart         # Smoke tests de inicialización de UI
└── pubspec.yaml                 # Dependencias y configuración de assets
```

---

## 🛠️ Instalación y Requisitos

- **Flutter SDK:** >= 3.24.0
- **Dart SDK:** >= 3.5.0
- **Navegador Web / Emulador Android / Dispositivo Físico**

### Pasos de Instalación:

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/renkaidev/Fiscalis-Frontend.git
   cd Fiscalis-Frontend
   ```

2. Obtener dependencias:
   ```bash
   flutter pub get
   ```

3. Ejecutar pruebas automatizadas:
   ```bash
   flutter test
   ```

---

## 🏃‍♂️ Ejecución

- **Modo Desarrollo Web (Servidor Local):**
  ```bash
  flutter run -d chrome
  # O para pruebas en red local:
  flutter run -d web-server --web-port=52400
  ```

- **Modo Android (Dispositivo o Emulador):**
  ```bash
  flutter run -d android
  ```

---

## 🧪 Matriz de Testing Automatizado

La aplicación cuenta con 19 pruebas automatizadas con 100% de aprobación:
- **`formatters_test.dart`**: Formato estricto de RUT con guión/puntos y formato de patente vehicular chilena de 6 dígitos.
- **`validators_test.dart`**: Algoritmo Módulo 11 chileno, campos opcionales para fuga y sanitización OWASP contra inyecciones.
- **`formulario_state_test.dart`**: Inmutabilidad del estado, retención de bytes de imagen en memoria sin depender de `dart:io` y coordenadas de contingencia.
- **`infraccion_model_test.dart`**: Compatibilidad estricta con el contrato de FastAPI backend.
- **`widget_test.dart`**: Inicialización y montaje del Splash Screen institucional.
