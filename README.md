# Sistema de Biblioteca

Aplicación web CRUD para gestionar el catálogo de libros, la comunidad lectora y los préstamos de una biblioteca.
Proyecto final de **Desarrollo de Proyectos con Software Libre** (Desarrollo e Integración del Sistema).

Todo el software usado es libre: **Python, Django, PostgreSQL, Gunicorn, Nginx, Ubuntu Server**.

## Qué hace

- **Libros:** crear, listar, buscar, editar y eliminar (con control de ejemplares disponibles).
- **Lectores:** crear, listar, buscar, editar y eliminar. El carnet (`LC-####`) se genera automáticamente.
- **Préstamos:** registrar y devolver préstamos. Al prestar baja el stock y al devolver sube.
- **Panel de inicio:** resumen en tiempo real (títulos, ejemplares, lectores, préstamos activos, vencidos y devueltos).
- **Usuarios y roles:** administración de cuentas y permisos desde la propia aplicación.
- **Cuentas de usuarios:** el Bibliotecario (y el Administrador) crea y consulta cuentas de estudiantes (rol Usuario), las busca por nombre, correo o carnet, ve cuántos préstamos activos, vencidos y devueltos tiene cada una y puede cambiarles la contraseña. No puede crear ni modificar cuentas de Bibliotecario o Administrador.

### Reglas de negocio

- Máximo 3 préstamos activos por lector.
- No se puede prestar dos veces el mismo libro al mismo lector mientras el préstamo siga activo.
- Un lector con un préstamo vencido no puede recibir nuevos préstamos.
- La fecha límite no puede estar en el pasado.
- No se puede eliminar un libro o lector que tiene historial de préstamos.
- No se puede prestar un libro sin ejemplares disponibles.

### Roles

| Rol | Permisos |
|---|---|
| **Administrador** | Todo: libros, lectores, préstamos, eliminar, Usuarios y roles y panel técnico `/admin/`. |
| **Bibliotecario** | Registrar préstamos y devoluciones; crear y editar libros y lectores; crear y administrar cuentas de estudiantes (rol Usuario) en *Cuentas de usuarios*. No elimina registros ni gestiona Bibliotecarios o Administradores. |
| **Usuario** | Consulta el catálogo y sus propios préstamos. Se vincula a un lector por el correo electrónico. |

## Tecnologías

- Python 3.12 o superior (probado con 3.14) y Django 5.2
- PostgreSQL (psycopg2)
- Gunicorn (servidor de aplicación) y Nginx (servidor web, proxy inverso)
- Whitenoise para archivos estáticos
- Ubuntu Server 26.04 LTS en una máquina virtual (VirtualBox)

## Estructura

```
biblioteca/     aplicación (modelos, vistas, formularios, permisos, comandos)
config/         configuración de Django (settings, urls, wsgi)
templates/      plantillas HTML
static/         CSS y JavaScript
deploy/         servicio de Gunicorn y sitio de Nginx
cargar_datos.py datos de demostración (opcional)
manage.py
requirements.txt
.env.example    plantilla de variables de entorno
```

## Instalación local (para probar en tu computadora)

Requisitos: Git, Python 3.12+ y PostgreSQL.

1. Crear la base de datos en PostgreSQL:

   ```sql
   CREATE USER app_user WITH PASSWORD 'tu_contraseña';
   CREATE DATABASE biblioteca_django OWNER app_user;
   ```

2. Clonar e instalar:

   ```bash
   git clone https://github.com/peterq161-cloud/sistema-biblioteca.git
   cd sistema-biblioteca
   python -m venv venv
   # Windows:  venv\Scripts\activate      Linux:  source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Crear el archivo `.env` a partir de la plantilla `.env.example` y poner tus valores
   (para desarrollo local puedes usar `DJANGO_DEBUG=True`).

4. Preparar la aplicación:

   ```bash
   python manage.py migrate
   python manage.py crear_roles
   python manage.py createsuperuser
   python cargar_datos.py          # opcional: libros, lectores y préstamos de ejemplo
   python manage.py runserver
   ```

5. Abrir `http://127.0.0.1:8000`.

## Despliegue en Linux (Ubuntu Server + Nginx + Gunicorn + PostgreSQL)

Así quedó desplegado el proyecto en la máquina virtual (IP de ejemplo `192.168.1.6`).

**1. Programas necesarios**

```bash
sudo apt update
sudo apt install -y postgresql nginx git python3-venv python3-pip libpq-dev unzip
```

**2. Base de datos**

```bash
sudo -u postgres psql -c "CREATE USER app_user WITH PASSWORD 'tu_contraseña';" \
                      -c "CREATE DATABASE biblioteca_django OWNER app_user;"
```

**3. Código y entorno de Python**

```bash
sudo mkdir -p /opt/sistema-biblioteca && sudo chown $USER:$USER /opt/sistema-biblioteca
git clone https://github.com/peterq161-cloud/sistema-biblioteca.git /opt/sistema-biblioteca
cd /opt/sistema-biblioteca
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**4. Configuración (`.env`)**

Copia `.env.example` a `.env` y completa los valores. Variables usadas:

```
DJANGO_SECRET_KEY=<clave larga y aleatoria>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.6
DJANGO_CSRF_TRUSTED_ORIGINS=http://192.168.1.6
DB_NAME=biblioteca_django
DB_USER=app_user
DB_PASSWORD=<contraseña de la base de datos>
DB_HOST=127.0.0.1
DB_PORT=5432
```

Permisos: el servicio corre como `www-data`, por lo que debe poder leer el archivo.

```bash
sudo chgrp www-data .env && sudo chmod 640 .env
```

**5. Tablas, roles, archivos estáticos y administrador**

```bash
set -a && . ./.env && set +a
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py crear_roles
venv/bin/python manage.py createsuperuser
venv/bin/python cargar_datos.py --yes     # opcional: datos de demostración
```

**6. Gunicorn como servicio**

```bash
sudo cp deploy/gunicorn-biblioteca.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-biblioteca
sudo systemctl status gunicorn-biblioteca --no-pager
```

Gunicorn escucha solo en `127.0.0.1:8001`.

**7. Nginx como proxy inverso**

Reemplaza `IP_DE_TU_SERVIDOR` por la IP real del servidor:

```bash
sed 's/IP_DE_TU_SERVIDOR/192.168.1.6/' deploy/nginx-biblioteca.conf | sudo tee /etc/nginx/sites-available/biblioteca > /dev/null
sudo ln -sf /etc/nginx/sites-available/biblioteca /etc/nginx/sites-enabled/biblioteca
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Nginx recibe las visitas en el puerto 80, entrega los archivos de `/static/` directamente
y pasa el resto de las peticiones a Gunicorn.

**8. Probar**

```bash
curl -I http://127.0.0.1        # debe responder 302 (redirige al login)
```

Desde otro equipo de la misma red: `http://192.168.1.6`.

## Comandos útiles

```bash
sudo systemctl restart gunicorn-biblioteca       # reiniciar la aplicación
sudo journalctl -u gunicorn-biblioteca -n 50     # ver errores de la aplicación
sudo tail -n 50 /var/log/nginx/error.log         # ver errores de Nginx
```

## Notas

- `.env` contiene secretos y **no se sube al repositorio** (está en `.gitignore`).
- `cargar_datos.py` borra los libros, lectores y préstamos existentes; úsalo solo en una base de datos de pruebas.
- Los usuarios nuevos no reciben privilegios automáticamente: el rol lo asigna un administrador desde **Usuarios y roles**.
