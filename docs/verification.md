# Verificación de la entrega

Comprobaciones locales realizadas el 7 de octubre de 2026. Los servicios externos conservan su estado **PENDIENDTE**.

## Interfaz en navegador

- Escritorio y anchuras de 320, 390, 768 y 1440 px: sin desbordamiento horizontal ni errores de React.
- Navegación móvil, perfiles de integrantes, reproducción de DOMINATION, búsqueda, filtro por categoría y estado sin coincidencias.
- Acceso: apertura, cambio a registro, cierre con Escape/botón y devolución del foco. Con Firebase sin configurar, el formulario indica PENDIENDTE y no crea cuentas ficticias.
- Con respuestas de API y widget controladas exclusivamente en la prueba: registro, cierre de sesión y conservación del token al pulsar la pestaña ya seleccionada.
- Publicación optimista: elemento visible con Guardando antes de responder la API; reemplazo al confirmar; eliminación al fallar, reapertura del borrador y reintento con el mismo UUID. Dos publicaciones confirmadas, sin duplicados.
- Contenido que incluye una etiqueta HTML permanece como texto; no se inserta un elemento ejecutable.

Las respuestas controladas comprueban el frontend y no acreditan integración real con Firebase o Turnstile. No se guardaron cuentas, claves de prueba ni mocks dentro de la aplicación.

## API local sin credenciales

- Honeypot lleno: 400 BOT_REJECTED.
- Origin ausente o incorrecto: 403 ORIGIN_REJECTED.
- Token CSRF incorrecto: 403 CSRF_REJECTED.
- JSON mayor de 16 KiB: 413 BODY_REJECTED.
- Primeros cinco intentos de acceso: servicio pendiente; sexto intento dentro del minuto: 429 RATE_LIMITED y Retry-After. En publicaciones, cinco envíos con honeypot se rechazan con 400 y el sexto con 429.
- Cookie CSRF: HttpOnly y SameSite=Strict; Secure se activa en producción.
- Arranque de producción normal: portada disponible, cabeceras de seguridad presentes y API pendiente rechazada con CONFIG_PENDING.

**PENDIENDTE:** la prueba local de producción con variables de origen/IP fue bloqueada por el control automático de ejecución ("blocked by policy"). La comprobación de Host, secreto de origen y filtrado de IP se revisó en código; debe probarse en el despliegue configurado junto con los pasos de [deployment.md](deployment.md).

## Compilación y dependencias

TypeScript, ESLint y compilación de producción completados correctamente. Todas las API, incluida la sesión, aparecen como dinámicas en la compilación final. Auditoría de dependencias de producción: cero vulnerabilidades reportadas tras actualizar las dependencias transitivas gRPC y UUID mediante overrides compatibles.

La auditoría completa mantiene un aviso de `braces@3.0.3` en herramientas de desarrollo de ESLint, sin versión corregida disponible durante la revisión. No se ejecutó una actualización forzada que cambiara el framework. La instalación avisa que los paquetes opcionales de Firebase AI/Functions declaran Node >=24.12, frente a Node 22.13 del entorno local; este proyecto no los importa. La compilación y las rutas utilizadas pasaron en el entorno local.

La validación con cuentas, Firestore, Redis compartido, Turnstile Siteverify y Cloudflare reales queda **PENDIENDTE** porque necesita la configuración humana solicitada.
