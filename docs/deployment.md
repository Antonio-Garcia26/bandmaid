# Despliegue y WAF: PENDIENDTE

Todos los pasos de cuentas, credenciales, dominios y publicación quedan **PENDIENDTE**. No se han creado servicios ni activado suscripciones. Usar Firebase Spark, Vercel Hobby, Cloudflare Free, Turnstile Free y Upstash Free.

## Firebase y Redis

1. Crear proyecto Firebase Spark y registrar una aplicación web. Activar Email/Password y una política de contraseñas equivalente a la validación del servidor. Añadir dominio autorizado.
2. Crear Firestore y publicar `firestore.rules` desde la pestaña Rules. No usar reglas abiertas de modo de prueba.
3. Generar credenciales Admin en Project settings → Service accounts. Configurar project ID, client email y private key exclusivamente como variables privadas. La private key conserva sus saltos de línea; admite la representación `\n` según el helper.
4. Copiar `.env.example` a `.env.local` y reemplazar PENDIENDTE. Al desplegar, introducir las mismas variables en Vercel. APP_ORIGIN debe ser la URL HTTPS exacta, sin rutas ni barra final.
5. Crear Redis en Upstash Free y copiar URL/token REST. No activar pay-as-you-go. Redis en producción coordina todos los servidores; el almacén local sirve solo para desarrollo.

## Turnstile

En Cloudflare → Turnstile, crear widget Managed gratuito. Añadir el hostname de producción y, en otro widget de desarrollo, los hostnames locales necesarios. Configurar NEXT_PUBLIC_TURNSTILE_SITE_KEY y TURNSTILE_SECRET_KEY. El frontend identifica acciones `register`, `login` y `create-post`; el servidor exige la acción y hostname correspondientes. Los tokens vencen y son de un solo uso.

Para probar, usar las [claves de prueba oficiales](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) exclusivamente en desarrollo. No rellenar claves ficticias ni desplegar claves de prueba en producción.

## Vercel

Importar el repositorio como Next.js. Instalar y construir con las órdenes predeterminadas. Configurar variables y APP_ORIGIN. Mantener Hobby para el proyecto escolar. `vercel.json` añade cabeceras y selecciona Next.js; **no es una definición del WAF**. El WAF se configura en el panel Firewall.

Se puede entregar en el subdominio gratuito vercel.app. Cloudflare DNS/WAF requiere una zona de un dominio que ya se posea; el registro de un dominio nuevo tiene coste independiente. La aplicación no exige comprar uno para revisar el frontend.

## Cloudflare DNS y TLS

**PENDIENDTE:** añadir el dominio en Vercel y seguir los registros DNS que indique ese proyecto; no copiar IP antiguas de tutoriales. En Cloudflare activar proxy naranja para el hostname del sitio y TLS **Full (strict)** cuando Vercel valide el certificado. Redirigir HTTP a HTTPS. Evitar caché de `/api/*`; las respuestas de sesión y CSRF usan no-store y no deben tener reglas de caché que lo sobrescriban.

## Reglas WAF gratuitas explícitas

Cloudflare → Security → Security rules → Create rule → Custom rule. Crear en este orden. Cloudflare Free permite cinco reglas custom, sin expresiones regulares. Los ejemplos usan operadores disponibles en Free; no necesitan `cf.bot_management.score`, Super Bot Fight Mode ni reglasets Enterprise.

1. **Known abusive IPs** — Action: **Block**. Crear una lista personalizada `bandmaid_blocked_ips` con IP observadas en registros y usar:

```text
ip.src in $bandmaid_blocked_ips
```

**PENDIENDTE:** poblar la lista con evidencia. No se inventan direcciones de supuestos atacantes. Alternativamente usar `ip.src in {192.0.2.10 2001:db8::10}` sustituyendo esas direcciones de documentación por IP reales. La aplicación también permite BLOCKED_IPS, separadas por coma, para bloqueo exacto.

2. **Block scanner paths** — Action: **Block**:

```text
starts_with(http.request.uri.path, "/.env") or
starts_with(http.request.uri.path, "/.git") or
starts_with(http.request.uri.path, "/wp-admin") or
http.request.uri.path eq "/wp-login.php" or
http.request.uri.path eq "/xmlrpc.php"
```

3. **Restrict API methods** — Action: **Block**:

```text
starts_with(http.request.uri.path, "/api/") and
not http.request.method in {"GET" "POST" "HEAD"}
```

4. **Challenge empty browser agents** — Action: **Managed Challenge**:

```text
http.user_agent eq "" and not cf.client.bot and
not starts_with(http.request.uri.path, "/api/")
```

No aplicar Managed Challenge indiscriminadamente a llamadas fetch del foro: esperan JSON. Las API usan Turnstile y rate limiting. La ausencia de User-Agent es una señal sencilla que puede falsificarse; acompaña las demás capas.

**PENDIENDTE:** comprobar Cloudflare Free Managed Ruleset y habilitar las protecciones gratuitas disponibles. Page Rules no implementan un WAF; estas son Security/Custom Rules.

## Impedir bypass y conservar la IP real

Para despliegue detrás de Cloudflare, el código admite una cabecera autenticada entre Cloudflare y Vercel:

1. **PENDIENDTE:** generar un secreto aleatorio privado de al menos 32 caracteres (por ejemplo, 32 bytes hexadecimales). Guardarlo en Vercel como `CLOUDFLARE_ORIGIN_SECRET`. Nunca usar prefijo NEXT_PUBLIC ni incluirlo en Git, navegador o respuestas.
2. En Cloudflare → Rules → Overview → Create rule → **Request Header Transform Rule**, crear regla para el hostname:

```text
http.host eq "TU-DOMINIO"
```

3. Configurar operaciones **Set**, que sobrescriben cualquier valor del visitante:

| Cabecera | Tipo | Valor |
| --- | --- | --- |
| x-bandmaid-origin | Set static | El mismo secreto privado de Vercel |
| x-bandmaid-client-ip | Set dynamic | `to_string(ip.src)` |

Request Header Transform Rules están disponibles en Free. No usar Add preservando valores del visitante. La ruta comprueba el secreto con comparación segura antes de confiar en esa IP. Si el secreto está configurado, solicitudes API sin él son rechazadas incluso al acceder directamente a Vercel. El proxy también lo exige, y las rutas mantienen la verificación propia.

Las páginas públicas pueden seguir siendo accesibles por el origen; el bloqueo de bypass de esta implementación protege las API de datos y autenticación. Para exigir Cloudflare también en todas las páginas, se puede añadir una regla de Vercel Firewall para bloquear el tráfico que no provenga de los [rangos Cloudflare](https://www.cloudflare.com/ips/), conservando acceso de revisión autorizado.

Sin CLOUDFLARE_ORIGIN_SECRET se permite el despliegue directo en Vercel, confiando solo en su cabecera de IP gestionada. Si se pone Cloudflare delante sin esta regla, el límite puede agrupar usuarios bajo la IP del proxy. Nunca habilitar confianza en una cabecera CF o X-Forwarded-For solo por su nombre.

## Verificación posterior: PENDIENDTE

- Registro/acceso reales y cierre de sesión; cookies HttpOnly, Secure y SameSite=Strict en HTTPS.
- Publicar con usuario real: aparición inmediata, confirmación Firestore y rollback cuando falla.
- Token Turnstile falso, expirado, reutilizado o con acción/hostname distinto: rechazar.
- Sexto intento en un minuto: HTTP 429, incluyendo diferentes instancias Vercel.
- CSRF ausente/incorrecto, Origin externo, honeypot lleno y cuerpo demasiado grande: rechazar.
- Escritura directa con SDK cliente: permission-denied por firestore.rules.
- IP bloqueada por WAF: Block; API directa al origen sin secreto: rechazo.
- Verificar que la IP dinámica coincide con la del visitante y no puede falsificarse mediante encabezados manuales.

## Documentación oficial

[Cloudflare custom rules y disponibilidad](https://developers.cloudflare.com/waf/custom-rules/), [transformación de cabeceras](https://developers.cloudflare.com/rules/transform/request-header-modification/create-dashboard/), [planes Transform Rules](https://developers.cloudflare.com/rules/transform/), [precios Firebase](https://firebase.google.com/pricing), [Turnstile Free](https://developers.cloudflare.com/turnstile/plans/), [Upstash Free](https://upstash.com/pricing/redis), [Vercel WAF](https://vercel.com/docs/vercel-firewall/vercel-waf/usage-and-pricing).
