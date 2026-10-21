# BAND-MAID · World Domination Club

**WORLD DOMINATION STARTS HERE.**

Cinco músicas. Un sonido imparable. Un lugar para quienes lo viven.

World Domination Club es una web escolar de fans de BAND-MAID. Reúne a las integrantes, sus videos y un espacio para conversar sobre música y conciertos. Su diseño combina fotografía de escenario, tipografía contundente y una paleta crema, negro y rojo, con navegación adaptada a escritorio y móvil.

![BAND-MAID en directo en Frankfurt](public/images/band-stage.png)

Fotografía de DragonFury · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) · [Fuente y créditos](docs/assets.md).

> Comunidad no oficial, sin afiliación con BAND-MAID ni sus representantes. El acceso O-MEI-SYU-SAMA de esta web corresponde únicamente al proyecto escolar.

## Qué puedes encontrar

- **Inicio:** portada, video destacado y acceso a las secciones de la comunidad.
- **La banda:** fotografías y perfiles interactivos de Miku Kobato, Saiki, Kanami, Akane y MISA.
- **Videos:** Choose me, DOMINATION, DICE y Sense, con reproducción de YouTube dentro de la web.
- **Comunidad:** publicaciones completas, búsqueda por título o contenido, filtros por tema y ordenación.
- **Club de fans:** formularios de registro, inicio y cierre de sesión preparados para Firebase Auth.
- **Publicaciones optimistas:** al enviar, el post aparece inmediatamente con «Guardando…». Si se confirma, queda publicado; si falla, se retira y se recupera el borrador para reintentar.

## Estado del proyecto

| Parte | Estado actual |
| --- | --- |
| Diseño y navegación | Implementados y revisados en escritorio y móvil. |
| Integrantes y videos | Disponibles sin configurar servicios externos. |
| Foro de ejemplo | Disponible y señalado como ejemplo mientras Firestore está sin configurar. |
| Registro, sesión y publicaciones reales | Formularios y API implementados; conexión y validación reales **PENDIENDTE**. |
| Seguridad de las API | Controles programados; claves, Redis y reglas externas **PENDIENDTE**. |
| Publicación del sitio | Configuración preparada; despliegue **PENDIENDTE**. |

La versión local permite recorrer el frontend. Los ejemplos del foro no son documentos guardados en Firestore. Para crear cuentas y publicar de verdad hay que completar la configuración siguiente.

## Ejecutar en local

```powershell
npm ci
npm run dev
```

Abre [localhost:3000](http://localhost:3000).

Para conectar los servicios, copia `.env.example` a `.env.local` y sustituye sus valores **PENDIENDTE**. Las credenciales privadas deben permanecer fuera del repositorio. La guía completa está en [docs/deployment.md](docs/deployment.md).

## Lo que falta para activar la web completa

Los siguientes pasos requieren intervención humana y quedan marcados **PENDIENDTE**. El objetivo es usar Firebase Spark, Vercel Hobby, Cloudflare Free, Turnstile Free y Upstash Free.

- [ ] **PENDIENDTE — Firebase:** crear el proyecto y la app web, activar Email/Password y crear Firestore.
- [ ] **PENDIENDTE — Credenciales:** configurar las variables web de Firebase y las credenciales privadas de Firebase Admin en `.env.local` y Vercel.
- [ ] **PENDIENDTE — Reglas de datos:** publicar `firestore.rules`; las escrituras del foro deben pasar por las API autorizadas.
- [ ] **PENDIENDTE — Turnstile:** crear el widget, registrar los hostnames y configurar site key y secret key.
- [ ] **PENDIENDTE — Redis:** configurar Upstash Free para compartir el límite de solicitudes entre instancias de producción.
- [ ] **PENDIENDTE — Vercel:** importar el repositorio, configurar las variables y `APP_ORIGIN`, y desplegar.
- [ ] **PENDIENDTE — Cloudflare:** configurar DNS, proxy, TLS, reglas WAF y la cabecera privada de origen que protege las API y conserva la IP del visitante.
- [ ] **PENDIENDTE — Pruebas reales:** comprobar registro, acceso, cierre de sesión, guardado en Firestore, tokens Turnstile, bloqueo de IP y límite de cinco solicitudes por minuto.

El subdominio de Vercel permite revisar la web sin comprar un dominio. Para usar tu propia zona de Cloudflare necesitas un dominio existente; registrar uno nuevo tiene un coste independiente.

## Desarrollo pendiente: próximas ampliaciones

Estas funciones todavía no están implementadas y forman la siguiente evolución del sitio:

- [ ] **Votos o reacciones:** guardar los votos por usuario. La ordenación «Más populares» ya consulta `likes`, pero las publicaciones nuevas empiezan en cero y todavía no se puede votar.
- [ ] **Comentarios:** responder a una publicación y mostrar conversaciones dentro del foro.
- [ ] **Gestión de publicaciones:** permitir que cada autor edite y elimine sus posts, con permisos comprobados en servidor.
- [ ] **Moderación:** añadir reportes de contenido y herramientas para revisar publicaciones.
- [ ] **Paginación:** cargar publicaciones anteriores; la API actual devuelve las 50 más recientes.
- [ ] **Recuperación de cuenta:** incorporar recuperación de contraseña y verificación de correo.
- [ ] **Pruebas automatizadas de integración:** cubrir autenticación, permisos y creación de publicaciones con un entorno de pruebas reproducible.

## Medidas de seguridad implementadas (Anti-Bots y Anti-Scraping)

El sitio web incorpora una estrategia de defensa en profundidad distribuida entre el middleware (`proxy.ts`), los endpoints de la API, las reglas de datos y el cliente React:

| Medida | Qué protege | Cómo funciona |
| --- | --- | --- |
| **Filtro de User-Agents y scrapers** | Toda la aplicación y rutas `/api/*` | `proxy.ts` y `validateUserAgent` analizan la cabecera `User-Agent`. Bloquean con HTTP 403 agentes vacíos o librerías de automatización (`curl`, `requests`, `httpx`, `scrapy`, `wget`, `selenium`, `puppeteer`, `playwright`, etc.). `robots.ts` restringe además rastreadores de IA. |
| **Telemetría e interacción humana** | Registro, inicio de sesión y creación de posts | El hook `useHumanTelemetry` detecta banderas de Webdriver (`navigator.webdriver`), curvatura de trayectorias del cursor y cadencia de teclado. `validateHumanInteraction` rechaza envíos con Webdriver, envíos en menos de 1.2 segundos, sin actividad física o con cadencia de tecleo sintética (<15 ms). |
| **CAPTCHA gráfico SVG dinámico** | Registro e inicio de sesión contra fuerza bruta | Genera imágenes SVG con filtros fractales de turbulencia y distorsión gaussiana en servidor. El token está firmado con HMAC-SHA256, expira en 5 minutos y se registra en memoria como consumido para impedir ataques de repetición (*anti-replay*). |
| **Trampa Honeypot** | Formularios de autenticación y publicaciones | Campo oculto `website` invisible para humanos. Si un script o bot automatizado lo completa, la solicitud se rechaza de inmediato con HTTP 400 (`BOT_REJECTED`). |
| **Anti-scraping SSR y carga diferida** | Fichas e información de integrantes (`#miembros`) | El HTML inicial (SSR) no incluye los datos, mostrando solo esqueletos vacíos. Los datos se solicitan a `/api/members` únicamente cuando un usuario humano interactúa o hace scroll visible (`IntersectionObserver`), exigiendo además la cabecera `X-Requested-With: XMLHttpRequest`. |
| **Selectores DOM dinámicos** | Elementos interactivos e inputs | El hook `useDynamicDomId` asigna prefijos y clases con semillas aleatorias por sesión (`_dyn_...`), impidiendo que scripts dependan de selectores estáticos rígidos como `By.ID("email")`. |
| **Límite de solicitudes (Rate Limiting)** | Endpoints del API contra DoS y fuerza bruta | Algoritmo de ventana deslizante por IP confiable y UID (Upstash Redis en producción, memoria en desarrollo). 5 peticiones/min para mutaciones y 30/min para captchas y lecturas. Al excederlo emite HTTP 429 con cabecera `Retry-After`. |
| **Protección CSRF y origen** | Mutaciones POST en API | Cookie HttpOnly protegida (`__Host-bandmaid_csrf` en producción, `SameSite=Strict`), comprobación de `Origin`, bloqueo de `Sec-Fetch-Site: cross-site` y validación estricta de la cabecera `X-CSRF-Token` en tiempo constante. |
| **Límite de tamaño de JSON** | Funciones serverless y consumo de memoria | `readBoundedJson` lee el cuerpo mediante streams con un límite de 16 KB (`MAX_JSON_BODY_BYTES`). Si se excede, aborta inmediatamente con HTTP 413 antes de parsear. |
| **Tiempo constante (Anti-Timing)** | Validación de tokens, CAPTCHA y secretos | `constantTimeMatch` utiliza `crypto.timingSafeEqual` para evitar ataques de canal lateral basados en medir microsegundos de respuesta. |
| **Reglas Zero-Trust en Firestore** | Base de datos Cloud Firestore | `firestore.rules` prohíbe todas las lecturas y escrituras directas desde el cliente (`allow read, write: if false;`). Todo acceso se gestiona de forma controlada desde el servidor con Firebase Admin SDK. |
| **Cabeceras de seguridad y CSP** | Navegador del cliente | Inyección global en `proxy.ts` de `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` y restricciones en `Permissions-Policy`. |
| **Cloudflare Turnstile** | Capa interactiva complementaria | Integrado en los formularios; valida el token emitido directamente contra la API de Cloudflare verificando el secreto, la acción esperada y el hostname. |

### Detalle de funcionamiento de los controles

1. **Defensa contra clientes automatizados:** Las peticiones a rutas protegidas pasan por una doble validación en `proxy.ts` y en los manejadores de ruta mediante `validateUserAgent` y `validateApiRequest`. Los scripts que no envían cabeceras de navegación estándar o que revelan firmas de librerías de scraping son detenidos en la frontera del servidor.
2. **Validación biomecánica del usuario:** Los formularios capturan datos de telemetría física en tiempo real sin requerir acciones adicionales del usuario legítimo. Un bot automatizado mediante Selenium o Puppeteer es detectado tanto por propiedades del entorno del navegador como por la ausencia de movimientos curvos del ratón o la velocidad instantánea de llenado.
3. **CAPTCHA sin servicios externos:** El sistema de CAPTCHA implementado en `lib/security/captcha.ts` funciona de forma autónoma. No depende de servicios de terceros para operar localmente o en entornos aislados, protegiendo contra fuerza bruta con firmas HMAC e invalidación inmediata tras el primer uso.
4. **Protección de datos públicos frente a extracción masiva:** La ficha de integrantes no se entrega pre-renderizada en el código fuente inicial. Requiere un cliente con JavaScript activo, desplazamiento real en el viewport y el envío de cabeceras de solicitud asíncrona legítima, neutralizando scrapers estáticos.
5. **Aislamiento de la base de datos:** Al denegar cualquier operación directa en `firestore.rules`, se garantiza que ninguna regla de negocio, validación de contenido, comprobación de sesión o rate limit pueda ser eludida conectándose directamente al proyecto de Firebase con las claves públicas del frontend.

Las reglas WAF complementarias para Cloudflare y la configuración de IP de origen están detalladas en [la guía de despliegue](docs/deployment.md). Las pruebas de auditoría y verificación contra estas protecciones están disponibles en la suite de [selenium/](selenium/README.md) y documentadas en [docs/verification.md](docs/verification.md).

## Arquitectura y archivos

La interfaz React interactúa con las API de Next.js mediante validaciones defensivas. El servidor valida cada operación, mantiene la sesión mediante cookies y usa Firebase Admin para acceder a Auth y Firestore. Las claves privadas y los secretos de verificación no se exponen al navegador.

```text
app/
  page.tsx, layout.tsx, globals.css    Página, tipografía y diseño
  robots.ts                           Directivas de rastreo y bloqueo de bots/IA
  api/auth/                          Registro, acceso, sesión, captcha y salida
  api/csrf/route.ts                   Generación de tokens CSRF
  api/members/route.ts                Entrega diferida y protegida de integrantes
  api/posts/route.ts                  Lectura y creación protegida de publicaciones
components/
  site/                              Portada, integrantes (lazy loading) y videos
  auth/                              Formularios protegidos y estado de sesión
  forum/                             Foro y creación optimista
  security/                          Componentes de TextCaptcha y Turnstile
  ui/Dialog.tsx                      Ventanas modales y diálogos accesibles
hooks/
  useHumanTelemetry.ts               Captura de telemetría y detección de Webdriver
  useDynamicDomId.ts                 Generación de IDs y clases dinámicas (DOM salting)
lib/
  firebase.ts, firebase-admin.ts      SDK web y conexión privada de administración
  api-client.ts, types.ts             Solicitudes de API y modelos tipados
  data.ts                            Integrantes, videos y catálogo base
  security/                          Módulos de seguridad, rate limit, captcha e IP
public/images/                       Fotografías y recursos gráficos
selenium/                            Scripts de auditoría, scraping y pruebas de seguridad
proxy.ts                             Middleware de filtrado, User-Agent y cabeceras
firestore.rules                      Reglas zero-trust para base de datos
.env.example                         Plantilla de variables de entorno
vercel.json                          Configuración de despliegue en Vercel
docs/                                Documentación de despliegue, pruebas y activos
```

**Tecnologías:** Next.js 16 App Router, React, TypeScript, Tailwind CSS, Firebase Auth y Firestore. En esta versión de Next.js, `proxy.ts` reemplaza la convención `middleware.ts`; los controles de las rutas también se ejecutan dentro de las API.

## Comprobaciones y documentación

```powershell
npm run lint
npx tsc --noEmit
npm run build
```

La compilación, TypeScript y ESLint pasaron. Se revisaron navegación móvil, perfiles, videos, filtros y publicación optimista con confirmación y recuperación ante fallos. Las pruebas con servicios reales siguen **PENDIENDTE**.

- [Configurar servicios, desplegar y activar el WAF](docs/deployment.md)
- [Pruebas realizadas y límites de la entrega](docs/verification.md)
- [Créditos de fotografías y videos](docs/assets.md)
- [Sitio oficial de BAND-MAID](https://bandmaid.tokyo/)
