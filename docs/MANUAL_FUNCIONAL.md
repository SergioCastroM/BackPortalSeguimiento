# Manual funcional — Plan de Acción 2026 · Portal de seguimiento

Este documento describe el uso de la aplicación desde el punto de vista del usuario: pantallas, flujos y permisos por rol.

---

## 1. Descripción general

La aplicación permite el **seguimiento trimestral de metas** del Plan de Acción 2026. Los usuarios pueden:

- **Administradores:** ver dashboards globales, gestionar secretarías, usuarios, cargar metas desde Excel, generar reportes y abrir/cerrar trimestres.
- **Secretarías:** ver el dashboard de su secretaría, listar sus metas y registrar el avance (seguimiento) por trimestre.

**Roles:** `admin` y `secretaria`. Cada usuario pertenece a una secretaría (excepto admin, que tiene visión global).

---

## 2. Acceso e inicio de sesión

### 2.1 URL y pantalla de login

- Abrir la URL del portal (por ejemplo la de Azure Static Web Apps o la de tu entorno).
- Si no hay sesión, se muestra la pantalla de **Inicio de sesión**.

### 2.2 Credenciales

- **Correo electrónico:** el asignado por el administrador.
- **Contraseña:** la proporcionada (o la que hayas cambiado).

Al enviar el formulario:

- Si las credenciales son correctas, se redirige según el rol:
  - **Admin** → `/admin/dashboard`
  - **Secretaría** → `/secretaria/dashboard`
- Si el sistema indica que debes **cambiar contraseña** (`requiere_cambio_password`), se redirige a la pantalla de cambio de contraseña (cuando esté disponible).
- Si las credenciales son incorrectas, se muestra el mensaje: *"Correo o contraseña incorrectos."*

### 2.3 Cerrar sesión

- En el menú lateral (sidebar) o en la barra superior, usar la opción **Cerrar sesión** para salir. Vuelves a la pantalla de login.

---

## 3. Usuario administrador

Tras iniciar sesión como **admin**, el menú lateral permite acceder a:

- Dashboard global  
- Secretarías  
- Usuarios  
- Carga Excel  
- Reportes  
- Trimestres  

### 3.1 Dashboard global

**Ruta:** `/admin/dashboard`

- **KPIs:** Total de metas, metas con seguimiento en el trimestre seleccionado, pendientes y % de cumplimiento promedio.
- **Filtro de trimestre:** selector T1 / T2 / T3 / T4 para cambiar el período.
- **Gráficos:**
  - **% Cumplimiento por secretaría:** barras por secretaría con código de colores (semáforo).
  - **Distribución por sector:** gráfico de dona (sectores: Educación, Salud, Gobierno, etc.).
  - **Evolución trimestral:** líneas de cumplimiento por secretaría a lo largo de T1–T4.
  - **Secretarías × Trimestres:** tabla tipo heatmap con el % por celda.

**Uso:** Revisar el estado general del plan y comparar secretarías y trimestres.

---

### 3.2 Secretarías

**Ruta:** `/admin/secretarias`

- **Tabla:** lista de secretarías con nombre, tipo y cantidad de metas.
- **Acción:** en cada fila, **Ver detalle** lleva al detalle de esa secretaría.

**Ruta:** `/admin/secretarias/:id` (detalle)

- Nombre de la secretaría.
- **KPIs:** Total metas, con seguimiento en el trimestre, % cumplimiento.
- **Tabla de metas:** lista de metas de esa secretaría con % de cumplimiento (o "—" si no hay seguimiento), con colores según nivel de avance.

**Uso:** Revisar el avance de cada secretaría y de sus metas.

---

### 3.3 Usuarios

**Ruta:** `/admin/usuarios`

- **Tabla:** usuarios del sistema con nombre, correo, rol (admin / secretaria) y secretaría asignada.
- Solo consulta; la creación/edición de usuarios se hace por otros medios (por ejemplo backend o administración de Azure/AD si se integra).

**Uso:** Ver quién tiene acceso y con qué rol y secretaría.

---

### 3.4 Carga Excel

**Ruta:** `/admin/excel`

Flujo en varios pasos:

1. **Subir archivo**
   - Arrastrar un archivo **.xlsx** a la zona indicada o hacer clic para seleccionarlo.
   - Tamaño máximo indicado en pantalla (p. ej. 10 MB).

2. **Procesamiento**
   - El sistema sube el archivo, lo procesa y muestra un estado de "Importando…".

3. **Vista previa**
   - **Resumen:** cantidad de filas **nuevas**, **actualizaciones** y **errores**.
   - **Metas por secretaría/oficina:** tabla con la cantidad de metas por oficina.
   - **Advertencias:** si las hay, se muestran en pantalla.
   - **Vista previa:** primeras filas del archivo para validar.

4. **Confirmar o cancelar**
   - **Confirmar importación:** aplica los cambios en la base de datos (nuevas metas y actualizaciones).
   - **Cancelar:** descarta la importación y vuelve a la zona de carga.

**Uso:** Cargar o actualizar el catálogo de metas desde una plantilla Excel definida por el sistema.

---

### 3.5 Reportes

**Ruta:** `/admin/reportes`

- **Filtros:** Año y trimestre (p. ej. 2026, T1).

**Tarjetas de reportes:**

| Reporte | Descripción | Acción disponible |
|--------|-------------|--------------------|
| **Por secretaría** | Seguimiento completo de una secretaría en el período | Seleccionar secretaría → **Excel** (descarga .xlsx). PDF en desarrollo. |
| **Consolidado total** | Resumen de todas las secretarías por trimestre | **Excel** (descarga). PDF en desarrollo. |
| **Por sector** | Metas agrupadas por sector (Educación, Salud, Gobierno) | Excel (según implementación). |
| **Pendientes** | Metas sin seguimiento en el trimestre activo | **Excel pendientes** (descarga). |

Los archivos se descargan con nombres sugeridos (p. ej. `reporte-secretaria-2026-T1.xlsx`, `pendientes-2026-T1.xlsx`).

**Uso:** Exportar datos para análisis externo o para reportes institucionales.

---

### 3.6 Trimestres

**Ruta:** `/admin/trimestres`

- **Tabla:** períodos de seguimiento (año, trimestre, estado, fecha límite).
- **Estados:** abierto, cerrado, próximo.
- **Acciones por período:**
  - **Abrir:** pone el trimestre en estado "abierto" (las secretarías pueden registrar seguimiento).
  - **Cerrar:** pone el trimestre en "cerrado" (ya no se registra seguimiento).

**Uso:** Controlar cuándo está habilitado el registro de seguimiento por trimestre.

---

## 4. Usuario secretaría

Tras iniciar sesión como **secretaría**, el menú muestra:

- Mi dashboard  
- Mis metas  

Solo se ven las metas de la **secretaría asignada** al usuario.

### 4.1 Mi dashboard

**Ruta:** `/secretaria/dashboard`

- **KPIs:** Total de metas, registradas en el trimestre (T1), pendientes y % de cumplimiento.
- **Gráfico esperado vs ejecutado:** barras por meta (valor esperado vs valor ejecutado).
- **Evolución acumulada:** línea de % de cumplimiento por trimestre (T1–T4) y valores en celdas.
- **Metas pendientes:** enlace o lista a metas que aún no tienen seguimiento en el trimestre; desde ahí se puede ir al detalle y registrar.

**Uso:** Tener una vista resumida del avance de la secretaría y de las metas pendientes.

---

### 4.2 Mis metas

**Ruta:** `/secretaria/metas`

- **Filtros:** búsqueda por texto y filtro por estado (Registrada / Pendiente).
- **Tabla paginada:** lista de metas de la secretaría (descripción, estado, etc.) con enlace a **detalle**.
- **Paginación:** cambio de página y tamaño de página (p. ej. 50 por página).

**Uso:** Buscar una meta concreta y abrir su detalle para ver o registrar seguimiento.

---

### 4.3 Detalle de meta

**Ruta:** `/secretaria/metas/:id`

- **Cabecera:** código del indicador, descripción, sector, estado (Registrada / Pendiente para el trimestre), meta cuatrienio.
- **Datos:** valor esperado 2026, proyecto MGA (valor, BPIN), % cumplimiento actual.
- **Avance trimestral:** bloques por T1–T4 con estado (registrada/pendiente) y botón **Registrar** para el trimestre correspondiente.
- **Botón general:** **Registrar seguimiento** abre el formulario de seguimiento para el trimestre elegido.

**Formulario de seguimiento (drawer lateral):**

- **Valor ejecutado** (obligatorio): valor numérico reportado.
- **Recursos ejecutados ($):** opcional.
- **% Cumplimiento:** se calcula automáticamente a partir del valor ejecutado y el valor esperado; se puede ajustar si aplica.
- **Evidencia / soporte** (obligatorio): texto (URL, acta, descripción).
- **Observaciones:** opcional.

Al **Guardar** se crea o actualiza el seguimiento para esa meta y trimestre/año; el drawer se cierra y el detalle se actualiza (estado y %).

**Uso:** Registrar o corregir el avance de una meta en un trimestre concreto.

---

## 5. Resumen de rutas por rol

| Ruta | Rol | Descripción |
|------|-----|-------------|
| `/login` | Todos | Inicio de sesión |
| `/admin/dashboard` | Admin | Dashboard global |
| `/admin/secretarias` | Admin | Lista de secretarías |
| `/admin/secretarias/:id` | Admin | Detalle secretaría |
| `/admin/usuarios` | Admin | Lista de usuarios |
| `/admin/excel` | Admin | Carga de metas desde Excel |
| `/admin/reportes` | Admin | Descarga de reportes (Excel/PDF) |
| `/admin/trimestres` | Admin | Apertura/cierre de trimestres |
| `/secretaria/dashboard` | Secretaría | Dashboard de la secretaría |
| `/secretaria/metas` | Secretaría | Lista de metas de la secretaría |
| `/secretaria/metas/:id` | Secretaría | Detalle y registro de seguimiento |

---

## 6. Mensajes y estados típicos

- **Cargando…:** se muestra mientras se obtienen datos del servidor.
- **Error al cargar:** fallo de red o del servidor; conviene reintentar o revisar conexión.
- **No se pudo cargar la meta:** la meta no existe o el usuario no tiene permiso (p. ej. meta de otra secretaría).
- **Correo o contraseña incorrectos:** credenciales inválidas en el login.
- **Etiquetas en metas:** "Registrada" (ya tiene seguimiento en el trimestre), "Pendiente" (aún no).
- **Colores de cumplimiento:** verdes/ámbar/rojos según el % (p. ej. ≥80 % verde, 50–80 % ámbar, <50 % rojo), tanto en tablas como en gráficos.

---

## 7. Consideraciones de uso

- **Trimestre activo:** muchas pantallas usan un trimestre por defecto (p. ej. T1 2026). El admin controla qué trimestres están abiertos en **Trimestres**.
- **Solo un seguimiento por meta y trimestre:** para una misma meta y período (año + trimestre) se crea un registro nuevo o se actualiza el existente.
- **Evidencia obligatoria:** no se puede guardar el seguimiento sin evidencia/soporte.
- **Excel:** el formato del archivo debe coincidir con la plantilla esperada por el sistema; en caso de errores, revisar el resumen y las advertencias en la vista previa.

Si necesitas una sección adicional (por ejemplo, glosario, capturas o flujos en diagrama), se puede ampliar este manual.
