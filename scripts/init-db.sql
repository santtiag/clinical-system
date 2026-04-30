-- Sistema Clínico - Script de Inicialización de Base de Datos
-- Crea múltiples bases de datos para cada microservicio

-- Base de datos para Identity Service
CREATE DATABASE identity_db;

-- Base de datos para Scheduling Service
CREATE DATABASE scheduling_db;

-- Base de datos para Medical Record Service
CREATE DATABASE medical_db;

-- Base de datos para Billing Service
CREATE DATABASE billing_db;

-- Base de datos para Reporting Service
CREATE DATABASE reporting_db;

-- Nota: Las conexiones se hacen directamente a cada base de datos
-- Este script se ejecuta automáticamente cuando el contenedor inicia
