# Sistema Clínico - Arquitectura de Microservicios

Sistema de gestión clínica basado en microservicios con FastAPI, aplicando Domain-Driven Design (DDD) y metodologías ágiles (XP).

## Arquitectura General

```
                                    ┌─────────────────────────────────────────────┐
                                    │              KONG API GATEWAY               │
                                    │   (Auth JWT, Rate Limit, Routing, Logs)    │
                                    └──────────────────┬──────────────────────────┘
                                                       │
          ┌──────────────────┬──────────────────┬──────┴──────┬──────────────────┐
          │                  │                  │             │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼─────┐  ┌────▼────┐   ┌──────▼──────┐
   │   Identity  │   │  Scheduling  │   │   Medical  │  │ Billing │  │  Reporting  │
   │   Service   │   │   Service   │   │   Record   │  │ Service │  │   Service   │
   │  (Puerto    │   │  (Puerto     │   │  (Puerto   │  │(Puerto  │  │  (Puerto    │
   │   8001)     │   │   8002)      │   │   8003)     │  │ 8004)   │  │   8005)      │
   └──────┬───────┘   └──────┬───────┘   └──────┬─────┘  └───┬────┘  └──────┬───────┘
          │                  │                  │             │                  │
          ▼                  ▼                  ▼             ▼                  ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ PostgreSQL  │    │ PostgreSQL  │    │ PostgreSQL  │ │ PostgreSQL  │ │ PostgreSQL  │
   │ (identity_db│    │(scheduling_ │    │ (medical_db │ │ (billing_db │ │(reporting_db│
   │             │    │    db)      │    │             │ │             │ │             │
   └─────────────┘    └─────────────┘    └─────────────┘ └─────────────┘ └─────────────┘
          │                  │                  │             │                  │
          └──────────────────┴────────┬─────────┴─────────────┴──────────────────┘
                                       │
                              ┌────────▼────────┐
                              │    RabbitMQ     │
                              │  (Event Bus)    │
                              └────────┬────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
   ┌──────▼──────┐              ┌───────▼──────┐              ┌───────▼──────┐
   │ Notification│              │    Audit     │              │   Logging    │
   │   Worker   │              │    Worker    │              │   (ELK)      │
   └─────────────┘              └──────────────┘              └──────────────┘
```

## Microservicios

| Servicio | Puerto | Descripción | Bounded Context |
|----------|--------|-------------|-----------------|
| Identity Service | 8001 | Registro, autenticación, perfiles | Gestión de Identidad |
| Scheduling Service | 8002 | Agendamiento de citas | Agendamiento |
| Medical Record Service | 8003 | Historias clínicas | Historia Clínica |
| Billing Service | 8004 | Facturación y pagos | Facturación |
| Reporting Service | 8005 | Reportes y analytics | Reportes |
| Admin Panel | 8006 | Dashboard administrativo | Administración |

## Workers (Background)

| Worker | Descripción |
|--------|-------------|
| Notification Worker | Procesa eventos y envía notificaciones (email/SMS) |
| Audit Worker | Registra logs de auditoría de todas las operaciones |

## Monitoreo y Observabilidad

| Componente | Puerto | Descripción |
|------------|--------|-------------|
| Kong API Gateway | 8000 | Punto de entrada, autenticación, rate limiting |
| Prometheus | 9090 | Métricas |
| Grafana | 3000 | Dashboards (admin/admin) |
| Loki | 3100 | Logs centralizados |
| Jaeger | 16686 | Distributed tracing |
| RabbitMQ Management | 15672 | UI de gestión de colas |

## Requisitos Funcionales

### RF-01: Gestión de Identidad y Acceso
- Registro de pacientes con validación de datos únicos (DNI, email)
- Registro de personal médico con información profesional
- Actualización de perfiles con historial de cambios
- Roles diferenciados: paciente, médico, administrador, staff

### RF-02: Agendamiento de Citas
- Consulta de disponibilidad por especialidad/fecha
- Reserva de citas con validación de horarios
- Cancelación y reprogramación
- Estados: programada, confirmada, en_atencion, completada, cancelada
- Notificaciones automáticas

### RF-03: Historia Clínica Electrónica
- Registro de prescripciones y medicamentos
- Consulta de historial completo
- Evolución del paciente
- Adjuntos de documentos

### RF-04: Facturación y Pagos
- Generación automática de recibos
- Integración con pasarela de pago
- Estados: pendiente, pagado, cancelado, reembolsado
- Reportes de ingresos

### RF-05: Reportes Médicos
- Estadísticas de consultas por especialidad
- Rendimiento del personal médico
- Diagnósticos más frecuentes
- Exportación PDF, Excel, CSV

## Requisitos No Funcionales

- **Escalabilidad**: Microservicios escalables horizontalmente
- **Seguridad**: JWT, HTTPS/TLS, logs de auditoría
- **Disponibilidad**: 99.5% uptime con redundancia
- **Rendimiento**: <2s para consultas, <5s para actualizaciones
- **Mantenibilidad**: Código documentado, tests automatizados

## Inicio Rápido

### Prerrequisitos
- Docker y Docker Compose instalados
- Git

### Levantar el ambiente

```bash
# Clonar o navegar al proyecto
cd sistema-clinico

# Iniciar todos los servicios
docker-compose up -d

# Verificar que todo esté corriendo
docker-compose ps

# Ver logs de un servicio
docker-compose logs -f identity-service

# Ver estado de salud
curl http://localhost:8000/health
```

### Endpoints de salud

```bash
# API Gateway
curl http://localhost:8000/health

# Microservicios
curl http://localhost:8001/health  # Identity
curl http://localhost:8002/health  # Scheduling
curl http://localhost:8003/health  # Medical Record
curl http://localhost:8004/health  # Billing
curl http://localhost:8005/health  # Reporting
curl http://localhost:8006/health  # Admin

# Monitoreo
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

### Acceso a dashboards

| Dashboard | URL | Credenciales |
|-----------|-----|--------------|
| Grafana | http://localhost:3000 | admin/admin |
| Jaeger | http://localhost:16686 | - |
| RabbitMQ | http://localhost:15672 | clinico/clinico_secret |
| Kong Manager | http://localhost:8001 | - |

### Registro de paciente (ejemplo)

```bash
# Registrar paciente
curl -X POST http://localhost:8001/auth/register/patient \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juanperez",
    "email": "juan@example.com",
    "password": "password123",
    "dni": "12345678",
    "firstName": "Juan",
    "lastName": "Pérez",
    "dateOfBirth": "1990-01-15"
  }'

# Login
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juanperez",
    "password": "password123"
  }'
```

## Estructura del Proyecto

```
sistema-clinico/
├── docker-compose.yml              # Orquestación de servicios
├── Kong/
│   └── kong.yml                   # Configuración del API Gateway
├── services/
│   ├── identity-service/          # Autenticación y usuarios
│   ├── scheduling-service/         # Citas y disponibilidad
│   ├── medical-record-service/    # Historias clínicas
│   ├── billing-service/           # Facturación
│   ├── reporting-service/         # Reportes
│   └── admin-panel/               # Panel admin
├── workers/
│   ├── notification-worker/       # Envío de notificaciones
│   └── audit-worker/              # Logs de auditoría
├── monitoring/
│   ├── prometheus.yml             # Config Prometheus
│   ├── grafana/                   # Dashboards y datasources
│   └── loki/                      # Config Loki
├── scripts/
│   └── init-db.sql               # Inicialización de BD
└── common/                        # Paquete compartido
    ├── config.py                  # Configuración
    ├── security.py                # JWT, password hashing
    ├── logging.py                 # Logging estructurado
    ├── database.py                # Conexión a BD
    ├── messaging.py              # RabbitMQ
    └── exceptions.py             # Excepciones personalizadas
```

## Tecnologías

- **Framework**: FastAPI (Python 3.11+)
- **Base de datos**: PostgreSQL (async con SQLAlchemy)
- **Mensajería**: RabbitMQ (aio-pika)
- **Cache**: Redis
- **API Gateway**: Kong
- **Monitoreo**: Prometheus, Grafana, Loki, Jaeger
- **Contenedores**: Docker, Docker Compose

## Metodología

- **Arquitectura**: Domain-Driven Design (DDD)
- **Metodología de desarrollo**: Extreme Programming (XP)
- **Comunicación entre servicios**: REST (síncrono) + RabbitMQ (asíncrono)
- **Patrones**: Repository, Service Layer, Event Sourcing

## Desarrollo Local

### Estructura de un microservicio

Cada microservicio sigue la estructura:

```
service-name/
├── src/
│   ├── domain/           # Entidades, servicios de dominio
│   ├── infrastructure/   # Repositorios, clientes externos
│   ├── presentation/     # Routers, schemas, main.py
│   └── main.py          # Punto de entrada
├── tests/               # Pruebas
├── Dockerfile
├── requirements.txt
└── ...
```

### Agregar un nuevo microservicio

1. Crear directorio en `services/`
2. Copiar estructura de otro servicio
3. Agregar al `docker-compose.yml`
4. Agregar ruta en `Kong/kong.yml`
5. Agregar scrape config en `monitoring/prometheus.yml`

## Pruebas

```bash
# Ejecutar pruebas de un servicio
docker exec clinico-identity-service pytest tests/

# Ver logs de un servicio
docker-compose logs -f identity-service
```

## Producción

Para despliegue en producción:

1. Configurar variables de entorno sensibles
2. Usar volumenes externos para datos persistentes
3. Configurar backups de PostgreSQL
4. Implementar Kubernetes para orquestación
5. Configurar SSL/TLS en Kong

## Licencia

MIT License