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

## Seguridad incluida

| Protección | Implementación |
| --- | --- |
| Turnstile | Widget en registro, acceso y publicación; verificación de token, acción y hostname en servidor. |
| Límite de solicitudes | Cinco intentos por minuto por IP; Redis en producción y memoria en desarrollo. Respuesta 429 con Retry-After. |
| Honeypot | Campo oculto en los formularios; rechazo en servidor si está lleno. |
| CSRF | Token aleatorio, cookie HttpOnly, comprobación de Origin y cabecera X-CSRF-Token. |
| Sesiones | Cookies HttpOnly, SameSite=Strict y Secure en producción; verificación de sesión antes de publicar. |
| Host e IP | Host permitido según APP_ORIGIN, lista de bloqueo y validación de la cabecera privada de Cloudflare. |
| Validación de contenido | Límites de tamaño y categorías permitidas; el contenido se muestra como texto escapado. |
| Firestore | Reglas que deniegan el acceso directo; operaciones mediante Firebase Admin desde el servidor. |

La falta de configuración obligatoria devuelve `CONFIG_PENDING`; en producción no se sustituye Redis por un almacén local ni se omite Turnstile.

Las reglas WAF y sus expresiones están en [la guía de despliegue](docs/deployment.md). Firebase Auth conserva endpoints públicos: los controles del formulario no garantizan impedir registros hechos directamente contra Firebase. La CSP admite scripts inline para la hidratación de Next.js. Estas limitaciones y las comprobaciones externas pendientes están documentadas en [docs/verification.md](docs/verification.md) y en la guía de despliegue.

## Arquitectura y archivos

La interfaz React llama a las API de Next.js. El servidor valida cada operación, mantiene la sesión mediante cookies y usa Firebase Admin para acceder a Auth y Firestore. Las claves privadas no llegan al navegador.

```text
app/
  page.tsx, layout.tsx, globals.css    Página, tipografía y diseño
  api/auth/                          Registro, acceso, sesión y salida
  api/csrf/route.ts                   Token CSRF
  api/posts/route.ts                  Lectura y creación de posts
components/
  site/                              Portada, integrantes y videos
  auth/                              Formularios y estado de sesión
  forum/                             Foro y creación optimista
  security/Turnstile.tsx              Verificación de formularios
  ui/Dialog.tsx                      Ventanas de perfiles y formularios
lib/
  firebase.ts, firebase-admin.ts      SDK web y conexión privada
  api-client.ts, types.ts             Solicitudes y contratos compartidos
  data.ts                            Integrantes, videos y ejemplos
  security/                          Validación, sesión y controles antibot
public/images/                       Fotografías y retratos
proxy.ts                             Filtro y cabeceras de seguridad
firestore.rules                      Permisos de acceso a datos
.env.example                         Variables PENDIENDTE
vercel.json                          Configuración de Vercel
docs/                                Despliegue, pruebas y créditos
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
