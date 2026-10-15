from django.db import models
from django.contrib.auth.models import User


class Libro(models.Model):
    titulo = models.CharField(max_length=150)
    autor = models.CharField(max_length=100)
    categoria = models.CharField(max_length=60, blank=True)
    editorial = models.CharField(max_length=100, blank=True)
    anio_publicacion = models.IntegerField('año de publicación', null=True, blank=True)
    isbn = models.CharField(max_length=20, unique=True)
    cantidad_total = models.IntegerField(default=1)
    cantidad_disponible = models.IntegerField(default=1)
    estado = models.CharField(max_length=20, default='Disponible')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo


class Lector(models.Model):
    nombre_completo = models.CharField(max_length=100)
    carnet = models.CharField(max_length=30, unique=True)
    correo = models.EmailField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo


class Prestamo(models.Model):
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    lector = models.ForeignKey(Lector, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='Activo')

    def __str__(self):
        return f'{self.libro} → {self.lector}'