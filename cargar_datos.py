import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from biblioteca.models import Libro, Lector, Prestamo


libros = [
    ('Cien años de soledad', 'Gabriel García Márquez', 'Novela', 'Sudamericana', 1967, '9780307474728', 3),
    ('Don Quijote de la Mancha', 'Miguel de Cervantes', 'Novela', 'Alfaguara', 1605, '9788420412146', 2),
    ('La sombra del viento', 'Carlos Ruiz Zafón', 'Misterio', 'Planeta', 2001, '9788408172178', 3),
    ('El principito', 'Antoine de Saint-Exupéry', 'Infantil', 'Salamandra', 1943, '9780156012195', 4),
    ('Rayuela', 'Julio Cortázar', 'Novela', 'Sudamericana', 1963, '9788437604572', 2),
    ('Pedro Páramo', 'Juan Rulfo', 'Novela', 'Fondo de Cultura', 1955, '9786071607881', 3),
    ('Ficciones', 'Jorge Luis Borges', 'Cuentos', 'Emecé', 1944, '9788491050100', 2),
    ('La casa de los espíritus', 'Isabel Allende', 'Novela', 'Plaza & Janés', 1982, '9788401337208', 3),
    ('El amor en los tiempos del cólera', 'Gabriel García Márquez', 'Novela', 'Oveja Negra', 1985, '9780307387264', 2),
    ('Crónica de una muerte anunciada', 'Gabriel García Márquez', 'Novela', 'Oveja Negra', 1981, '9780307475978', 3),
]

lectores = [
    ('Juan Pérez', 'A001', 'juan.perez@correo.com', '809-555-0101'),
    ('María López', 'A002', 'maria.lopez@correo.com', '809-555-0102'),
    ('Carlos Díaz', 'A003', 'carlos.diaz@correo.com', '809-555-0103'),
    ('Ana Martínez', 'A004', 'ana.martinez@correo.com', '809-555-0104'),
    ('Luis Ramírez', 'A005', 'luis.ramirez@correo.com', '809-555-0105'),
    ('Laura Santos', 'A006', 'laura.santos@correo.com', '809-555-0106'),
    ('Pedro Gómez', 'A007', 'pedro.gomez@correo.com', '809-555-0107'),
    ('Sofía Reyes', 'A008', 'sofia.reyes@correo.com', '809-555-0108'),
    ('Miguel Torres', 'A009', 'miguel.torres@correo.com', '809-555-0109'),
    ('Carmen Núñez', 'A010', 'carmen.nunez@correo.com', '809-555-0110'),
]

prestamos = [
    ('9780307474728', 'A001', date(2026, 10, 20), 'Activo'),
    ('9788420412146', 'A002', date(2026, 10, 21), 'Activo'),
    ('9788408172178', 'A003', date(2026, 10, 22), 'Activo'),
    ('9780156012195', 'A004', date(2026, 10, 23), 'Activo'),
    ('9788437604572', 'A005', date(2026, 10, 24), 'Devuelto'),
    ('9786071607881', 'A006', date(2026, 10, 25), 'Activo'),
    ('9788491050100', 'A007', date(2026, 10, 26), 'Devuelto'),
    ('9788401337208', 'A008', date(2026, 10, 27), 'Activo'),
    ('9780307387264', 'A009', date(2026, 10, 28), 'Activo'),
    ('9780307475978', 'A010', date(2026, 10, 29), 'Activo'),
]

for titulo, autor, cat, editorial, anio, isbn, total in libros:
    Libro.objects.get_or_create(isbn=isbn, defaults={
        'titulo': titulo, 'autor': autor, 'categoria': cat,
        'editorial': editorial, 'anio_publicacion': anio,
        'cantidad_total': total, 'cantidad_disponible': total,
        'estado': 'Disponible',
    })

for nombre, carnet, correo, telefono in lectores:
    Lector.objects.get_or_create(carnet=carnet, defaults={
        'nombre_completo': nombre, 'correo': correo, 'telefono': telefono,
    })

usuario = User.objects.filter(is_superuser=True).first()

for isbn, carnet, devolucion, estado in prestamos:
    libro = Libro.objects.get(isbn=isbn)
    lector = Lector.objects.get(carnet=carnet)
    Prestamo.objects.get_or_create(libro=libro, lector=lector, defaults={
        'usuario': usuario, 'fecha_devolucion': devolucion, 'estado': estado,
    })

print('Libros:', Libro.objects.count())
print('Lectores:', Lector.objects.count())
print('Préstamos:', Prestamo.objects.count())
