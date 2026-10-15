from django.contrib import admin
from django.db import transaction, connection

from .forms import LectorForm, LibroForm
from .models import Lector, Libro, Prestamo


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    # Usa el mismo formulario que la web: valida el ISBN y calcula las existencias.
    form = LibroForm
    list_display = ('titulo', 'autor', 'isbn', 'cantidad_disponible', 'cantidad_total', 'estado')
    search_fields = ('titulo', 'autor', 'isbn')
    list_filter = ('estado', 'categoria')


@admin.register(Lector)
class LectorAdmin(admin.ModelAdmin):
    form = LectorForm
    list_display = ('nombre_completo', 'carnet', 'correo', 'telefono')
    search_fields = ('nombre_completo', 'carnet')

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if not change:
                if connection.vendor == 'postgresql':
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [741852963])
                obj.carnet = LectorForm.siguiente_carnet()
            super().save_model(request, obj, form, change)



@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    """Solo consulta: los préstamos se registran y devuelven desde la web,
    porque ahí se controlan las existencias y las reglas de negocio."""
    list_display = ('libro', 'lector', 'fecha_prestamo', 'fecha_devolucion', 'estado', 'usuario')
    list_filter = ('estado',)
    search_fields = ('libro__titulo', 'lector__nombre_completo')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Acceso al sitio administrativo reservado al rol Administrador.
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser


# Solo superusuarios acceden al panel administrativo de Django.
admin.site.has_permission = lambda request: bool(request.user.is_active and request.user.is_superuser)
