# Manual de uso – Sistema de Biblioteca

Este documento explica qué puede hacer cada tipo de persona dentro del sistema y cómo se usa cada módulo. Hay tres roles: **Administrador**, **Bibliotecario** y **Usuario** (el estudiante que pide libros).

El sistema se abre desde el navegador en la dirección de la máquina virtual (por ejemplo `http://192.168.1.10/`). Lo primero que aparece es el inicio de sesión.

## Resumen rápido

| Módulo | Administrador | Bibliotecario | Usuario |
|---|---|---|---|
| Visión general (inicio) | Sí | Sí | Sí (solo sus datos) |
| Catálogo de libros | Ver, crear, editar, eliminar | Ver, crear, editar | Solo ver |
| Comunidad lectora | Ver, crear, editar, eliminar | Ver, crear, editar | No tiene acceso |
| Préstamos | Todo | Registrar, editar, devolver | Solo ve los suyos |
| Cuentas de usuarios | Sí | Sí | No (error 403) |
| Usuarios y roles | Sí | No (error 403) | No (error 403) |
| Panel `/admin/` de Django | Sí | No | No |

---

## 1. Administrador

Es el que tiene control de todo. Se reconoce porque en el menú de la izquierda tiene la opción **Usuarios y roles**.

### Visión general
Muestra los números del momento: títulos, ejemplares, lectores, préstamos activos, vencidos y devueltos.

### Catálogo de libros
- **Crear:** botón *Nuevo libro*. Se llenan título, autor, categoría, editorial, año, ISBN y cantidad. El ISBN no se puede repetir.
- **Buscar:** la barra de arriba filtra por título, autor o ISBN.
- **Editar:** botón *Editar* de cada fila.
- **Eliminar:** solo el administrador puede. Si el libro ya tiene préstamos en su historial, el sistema no lo deja borrar y muestra un aviso.

### Comunidad lectora
- Aquí se registran las personas que piden libros. El carnet (`LC-####`) lo genera el sistema solo.
- Se puede buscar, editar y eliminar. No se puede eliminar un lector con préstamos en su historial.

### Préstamos
- **Registrar:** se elige el lector y el libro, y la fecha límite. Al guardar, el libro baja una unidad de disponibles.
- **Devolver:** botón *Devolver*, pide confirmación. El libro sube una unidad.
- **Editar:** un préstamo activo solo permite cambiar la fecha límite.
- **Eliminar:** solo el administrador.
- Reglas: máximo 3 préstamos activos por lector, no se repite el mismo libro al mismo lector, y quien tenga un préstamo vencido no puede sacar otro.

### Cuentas de usuarios
Aquí se crean las cuentas de los estudiantes. Para crear una cuenta primero tiene que existir el lector, y el **correo de la cuenta debe ser el mismo que el del lector**; así queda enlazada. También se puede ver cuántos préstamos tiene la persona y cambiarle la contraseña.

### Usuarios y roles
Solo para el personal: se crean, editan y eliminan cuentas de **Administrador** y **Bibliotecario**. Los estudiantes no aparecen aquí, se manejan en *Cuentas de usuarios*. El sistema no deja eliminar al último administrador.

### Panel `/admin/`
Es el panel interno de Django, solo para el administrador. Se usa para revisar datos en caso de necesidad.

---

## 2. Bibliotecario

Es quien atiende el mostrador. Entra y ve: Visión general, Catálogo de libros, Comunidad lectora, Préstamos y Cuentas de usuarios.

- **Libros:** puede crear y editar. No puede eliminar.
- **Lectores:** puede crear y editar. No puede eliminar.
- **Préstamos:** registra préstamos, los devuelve y cambia la fecha límite. Se aplican las mismas reglas de siempre (límite de 3, vencidos, stock).
- **Cuentas de usuarios:** crea cuentas para estudiantes, las consulta y les cambia la contraseña. No puede tocar cuentas de Bibliotecario ni de Administrador.
- Si intenta entrar a **Usuarios y roles** (`/usuarios/`) el sistema responde 403 (sin permiso).

### Flujo típico en el mostrador
1. Buscar al lector en *Comunidad lectora* (o crearlo si es nuevo).
2. Ir a *Préstamos → Nuevo préstamo*, escoger lector y libro.
3. Cuando el estudiante devuelve el libro, buscar el préstamo y pulsar *Devolver*.

---

## 3. Usuario (estudiante)

Es la persona que usa la biblioteca. Su cuenta la crea el bibliotecario o el administrador y queda enlazada a su ficha de lector por el correo.

- **Catálogo de libros:** puede consultar y buscar, solo lectura. No tiene botones de crear, editar ni eliminar.
- **Préstamos:** ve únicamente sus propios préstamos (activos, vencidos y devueltos).
- **Inicio:** ve el resumen de sus datos.
- No ve *Comunidad lectora* ni *Cuentas de usuarios*. Si escribe esas direcciones a mano, recibe error 403.

---

## Datos que se guardan

Todo queda en PostgreSQL (base `biblioteca_django`): libros, lectores, préstamos y las cuentas. Si se reinicia el servidor los datos siguen ahí. La conexión a la base de datos es persistente (`CONN_MAX_AGE = 60` en `config/settings.py`).
