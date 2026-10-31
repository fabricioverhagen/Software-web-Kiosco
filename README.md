# Software Web Kiosco

Sistema de gestión para kiosco y comercio minorista desarrollado con Flask y SQLite. Permite gestionar usuarios, clientes, proveedores, productos, ventas, facturas, cajas y dashboard de estadísticas, con aislamiento total de datos por usuario autenticado.

## Descripción

`Software Web Kiosco` es una aplicación web de control interno para negocios de venta minorista, pensada para operar con múltiples cuentas de usuario en un mismo entorno. Cada usuario registra e inicia sesión con su propia cuenta y visualiza únicamente sus propios datos: productos, clientes, proveedores, facturas, ventas y cajas.

El proyecto incluye:

- autenticación de usuarios
- registro e inicio de sesión
- dashboard con métricas y alertas
- gestión de productos
- gestión de clientes
- gestión de proveedores
- control de ventas y facturación
- seguimiento de factura por proveedor
- apertura y cierre de caja
- gestión de stock
- aislamiento total por usuario mediante `id_usuario`

## Stack tecnológico

- Python 3.10+
- Flask
- SQLite
- HTML / CSS / JavaScript
- Jinja2

## Estructura del proyecto

```text
Software-web-Kiosco/
├── app.py                  # Aplicación principal Flask
├── basededatosflask.db     # Base de datos SQLite
├── requirements.txt        # Dependencias del proyecto
├── dev-requirements.txt    # Dependencias de desarrollo
├── pyproject.toml          # Configuración de proyecto
├── README.md               # Documentación del proyecto
├── static/                 # Archivos estáticos (CSS, JS, uploads)
├── templates/              # Plantillas HTML
├── tests/                  # Pruebas automatizadas
├── .venv/                  # Entorno virtual (local)
└── .gitignore              # Archivos ignorados por Git
```

## Requisitos previos

- Python 3.10 o superior
- Git
- Entorno virtual recomendado

## Configuración de la base de datos

La aplicación usa SQLite con la base de datos `basededatosflask.db`.

La base de datos está diseñada para soportar múltiples usuarios con aislamiento total de datos mediante el campo `id_usuario` en cada tabla relevante. Esto garantiza que cada cuenta solo pueda ver y operar sobre sus propios registros.

## Funcionalidades principales

### 1. Autenticación y multiusuario

- Registro de usuario nuevo
- Inicio de sesión con email y contraseña
- Sesión por cuenta autenticada
- Datos aislados por `id_usuario`

### 2. Dashboard

- estadísticas del día
- totales por ventas
- conteo de clientes
- productos con stock bajo
- indicadores clave del negocio

### 3. Gestión de productos

- alta de productos
- edición
- eliminación
- control de stock
- validación de código de barras por usuario

### 4. Gestión de clientes

- registro de clientes
- edición y eliminación
- visualización independiente por usuario

### 5. Gestión de proveedores

- alta/edición de proveedores
- facturas asociadas por proveedor
- carga de archivos PDF

### 6. Ventas y facturación

- generación de ventas
- asociación con cliente
- cálculo de subtotal y total
- registro de método de pago
- control de stock automático

### 7. Cajas

- apertura de caja
- cierre de caja
- monto de apertura y cierre
- historial por usuario





## Licencia

Este proyecto se distribuye con fines educativos y de desarrollo interno. Revisa el contenido del repositorio para consultar condiciones adicionales si aplica.

## Autor

Proyecto desarrollado por el equipo del sistema de gestión de kiosco.

---

