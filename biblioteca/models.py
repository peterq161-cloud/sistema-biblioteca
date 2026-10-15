from django.contrib.auth.models import User
from django.db import models
from datetime import date
from datetime import date


class Libro(models.Model):
    titulo = models.CharField(max_length=150)
    autor = models.CharField(max_length=100)
    categoria = models.CharField(max_length=60, blank=True)
    editorial = models.CharField(max_length=100, blank=True)
    anio_publicacion = models.IntegerField('año de publicación', null=True, blank=True)
    isbn = models.CharField('ISBN', max_length=20, unique=True)
    cantidad_total = models.IntegerField(default=1)
    cantidad_disponible = models.IntegerField(default=1)
    estado = models.CharField(max_length=20, default='Disponible')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'libro'
        verbose_name_plural = 'libros'

    def __str__(self):
        return self.titulo


class Lector(models.Model):
    nombre_completo = models.CharField(max_length=100)
    carnet = models.CharField(max_length=30, unique=True)
    correo = models.EmailField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'lector'
        verbose_name_plural = 'lectores'

    def __str__(self):
        return self.nombre_completo


class Prestamo(models.Model):
    # fecha_devolucion: mientras el préstamo está Activo es la fecha límite;
    # al devolver el libro se reemplaza por la fecha real de devolución.
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    lector = models.ForeignKey(Lector, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion = models.DateField('fecha de devolución', null=True, blank=True)
    estado = models.CharField(max_length=20, default='Activo')

    class Meta:
        verbose_name = 'préstamo'
        verbose_name_plural = 'préstamos'

    def __str__(self):
        return f'{self.libro} → {self.lector}'

    @property
    def dias_retraso(self):
        return max(0, (date.today() - self.fecha_devolucion).days) if self.esta_vencido else 0

    @property
    def esta_vencido(self):
        return (
            self.estado == 'Activo'
            and self.fecha_devolucion is not None
            and self.fecha_devolucion < date.today()
        )
