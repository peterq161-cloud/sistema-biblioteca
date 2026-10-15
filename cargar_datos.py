"""Carga datos de demostración coherentes en el Sistema de Biblioteca.

Uso (con el entorno virtual activo, en la carpeta donde está manage.py):
    python cargar_datos.py          pide confirmación antes de borrar
    python cargar_datos.py --yes    no pregunta

ATENCIÓN: borra todos los libros, lectores y préstamos actuales.
No toca a los usuarios (tu superusuario se conserva).
"""
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

# Detecta el módulo de settings leyendo manage.py, así funciona con cualquier nombre de proyecto.
texto = Path(__file__).with_name('manage.py').read_text(encoding='utf-8')
modulo = re.search(r"DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)['\"]", texto).group(1)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', modulo)

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.db import transaction  # noqa: E402

from biblioteca.models import Lector, Libro, Prestamo  # noqa: E402

LIBROS = [
    # título, autor, categoría, editorial, año, isbn, ejemplares
    ('Cien años de soledad', 'Gabriel García Márquez', 'Novela', 'Sudamericana', 1967, '9780307474728', 3),
    ('Don Quijote de la Mancha', 'Miguel de Cervantes', 'Clásico', 'Real Academia Española', 1605, '9788420412146', 2),
    ('La ciudad y los perros', 'Mario Vargas Llosa', 'Novela', 'Seix Barral', 1963, '9788432217159', 2),
    ('Rayuela', 'Julio Cortázar', 'Novela', 'Alfaguara', 1963, '9788420471891', 1),
    ('El túnel', 'Ernesto Sabato', 'Novela', 'Seix Barral', 1948, '9788432216749', 2),
    ('Ficciones', 'Jorge Luis Borges', 'Cuento', 'Alianza Editorial', 1944, '9788420633121', 2),
    ('Pedro Páramo', 'Juan Rulfo', 'Novela', 'Cátedra', 1955, '9788437604831', 1),
    ('Historia de la eternidad', 'Jorge Luis Borges', 'Ensayo', 'Alianza Editorial', 1936, '9788420633138', 1),
    ('Introducción a los algoritmos', 'Thomas H. Cormen', 'Informática', 'MIT Press', 2009, '9780262033848', 3),
    ('Fundamentos de bases de datos', 'Abraham Silberschatz', 'Informática', 'McGraw-Hill', 2019, '9788448190330', 2),
]

LECTORES = [
    ('Ana Martínez Peña', 'LC-1001', 'ana.martinez@example.com', '809-555-0101'),
    ('Luis Fernández Rojas', 'LC-1002', 'luis.fernandez@example.com', '809-555-0102'),
    ('María López Díaz', 'LC-1003', 'maria.lopez@example.com', '829-555-0103'),
    ('Carlos Ramírez Soto', 'LC-1004', 'carlos.ramirez@example.com', '849-555-0104'),
    ('Sofía Castillo Núñez', 'LC-1005', 'sofia.castillo@example.com', '809-555-0105'),
    ('Pedro Gómez Vargas', 'LC-1006', 'pedro.gomez@example.com', '829-555-0106'),
    ('Laura Jiménez Cruz', 'LC-1007', 'laura.jimenez@example.com', '849-555-0107'),
    ('Miguel Santos Reyes', 'LC-1008', 'miguel.santos@example.com', '809-555-0108'),
    ('Elena Pérez Mora', 'LC-1009', 'elena.perez@example.com', '829-555-0109'),
    ('Javier Torres Luna', 'LC-1010', 'javier.torres@example.com', '849-555-0110'),
]

# índice de libro, índice de lector, días desde hoy en que se prestó, estado
# Plazo de 14 días: los activos con préstamo de hace más de 14 días quedan vencidos.
PRESTAMOS = [
    (0, 0, -3, 'Activo'),
    (0, 1, -5, 'Activo'),
    (1, 2, -20, 'Activo'),    # vencido
    (2, 3, -2, 'Activo'),
    (3, 4, -18, 'Activo'),    # vencido (Rayuela queda agotado)
    (8, 5, -6, 'Activo'),
    (8, 0, -1, 'Activo'),
    (5, 6, -30, 'Devuelto'),
    (6, 7, -25, 'Devuelto'),
    (9, 8, -40, 'Devuelto'),
]


def confirmar():
    if '--yes' in sys.argv:
        return True
    print('Esto BORRARÁ todos los libros, lectores y préstamos actuales.')
    return input('Escribe SI para continuar: ').strip().upper() == 'SI'


@transaction.atomic
def cargar(usuario):
    Prestamo.objects.all().delete()
    Libro.objects.all().delete()
    Lector.objects.all().delete()

    libros = [Libro.objects.create(
        titulo=t, autor=a, categoria=c, editorial=e, anio_publicacion=y,
        isbn=i, cantidad_total=n, cantidad_disponible=n, estado='Disponible')
        for t, a, c, e, y, i, n in LIBROS]
    lectores = [Lector.objects.create(nombre_completo=n, carnet=c, correo=m, telefono=t)
                for n, c, m, t in LECTORES]

    hoy = date.today()
    for li, le, dias, estado in PRESTAMOS:
        prestado = hoy + timedelta(days=dias)
        if estado == 'Activo':
            fecha = prestado + timedelta(days=14)          # fecha límite
            libros[li].cantidad_disponible -= 1
        else:
            fecha = prestado + timedelta(days=10)          # fecha real de devolución
        p = Prestamo.objects.create(libro=libros[li], lector=lectores[le], usuario=usuario,
                                    fecha_devolucion=fecha, estado=estado)
        # fecha_prestamo es auto_now_add: se corrige con update
        Prestamo.objects.filter(pk=p.pk).update(fecha_prestamo=prestado)

    for libro in libros:
        libro.estado = 'Disponible' if libro.cantidad_disponible > 0 else 'Agotado'
        libro.save()


if __name__ == '__main__':
    usuario = User.objects.filter(is_superuser=True).order_by('id').first()
    if usuario is None:
        sys.exit('No hay superusuario. Crea uno primero: python manage.py createsuperuser')
    if not confirmar():
        sys.exit('Cancelado. No se cambió nada.')
    cargar(usuario)
    print(f'Listo: {Libro.objects.count()} libros, {Lector.objects.count()} lectores, '
          f'{Prestamo.objects.count()} préstamos.')
