from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Libro, Lector, Prestamo


@login_required
def inicio(request):
    contexto = {
        'total_libros': Libro.objects.count(),
        'total_lectores': Lector.objects.count(),
        'total_prestamos': Prestamo.objects.count(),
    }
    return render(request, 'inicio.html', contexto)


class Base(LoginRequiredMixin):
    nombre = ''
    encabezado = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['encabezado'] = self.encabezado
        ctx['url_lista'] = f'{self.nombre}_lista'
        ctx['url_nuevo'] = f'{self.nombre}_nuevo'
        ctx['url_editar'] = f'{self.nombre}_editar'
        ctx['url_eliminar'] = f'{self.nombre}_eliminar'
        return ctx

    def get_success_url(self):
        return reverse(f'{self.nombre}_lista')


class ListaBase(Base, ListView):
    template_name = 'crud/lista.html'
    campos = []

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['columnas'] = [
            str(self.model._meta.get_field(c).verbose_name).capitalize()
            for c in self.campos
        ]
        ctx['filas'] = [
            (obj, [getattr(obj, c) for c in self.campos])
            for obj in ctx['object_list']
        ]
        return ctx


class NuevoBase(Base, CreateView):
    template_name = 'crud/form.html'


class EditarBase(Base, UpdateView):
    template_name = 'crud/form.html'


class EliminarBase(Base, DeleteView):
    template_name = 'crud/eliminar.html'


# ---------- Libros ----------
class LibroLista(ListaBase):
    model = Libro
    nombre = 'libro'
    encabezado = 'Libros'
    campos = ['titulo', 'autor', 'isbn', 'cantidad_disponible', 'estado']

class LibroNuevo(NuevoBase):
    model = Libro
    nombre = 'libro'
    encabezado = 'Nuevo libro'
    fields = ['titulo', 'autor', 'categoria', 'editorial', 'anio_publicacion',
              'isbn', 'cantidad_total', 'cantidad_disponible', 'estado']

class LibroEditar(EditarBase):
    model = Libro
    nombre = 'libro'
    encabezado = 'Editar libro'
    fields = ['titulo', 'autor', 'categoria', 'editorial', 'anio_publicacion',
              'isbn', 'cantidad_total', 'cantidad_disponible', 'estado']

class LibroEliminar(EliminarBase):
    model = Libro
    nombre = 'libro'
    encabezado = 'Eliminar libro'


# ---------- Lectores ----------
class LectorLista(ListaBase):
    model = Lector
    nombre = 'lector'
    encabezado = 'Lectores'
    campos = ['nombre_completo', 'carnet', 'correo', 'telefono']

class LectorNuevo(NuevoBase):
    model = Lector
    nombre = 'lector'
    encabezado = 'Nuevo lector'
    fields = ['nombre_completo', 'carnet', 'correo', 'telefono']

class LectorEditar(EditarBase):
    model = Lector
    nombre = 'lector'
    encabezado = 'Editar lector'
    fields = ['nombre_completo', 'carnet', 'correo', 'telefono']

class LectorEliminar(EliminarBase):
    model = Lector
    nombre = 'lector'
    encabezado = 'Eliminar lector'


# ---------- Préstamos ----------
class PrestamoLista(ListaBase):
    model = Prestamo
    nombre = 'prestamo'
    encabezado = 'Préstamos'
    campos = ['libro', 'lector', 'usuario', 'fecha_prestamo', 'fecha_devolucion', 'estado']

class PrestamoNuevo(NuevoBase):
    model = Prestamo
    nombre = 'prestamo'
    encabezado = 'Nuevo préstamo'
    fields = ['libro', 'lector', 'fecha_devolucion', 'estado']

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class PrestamoEditar(EditarBase):
    model = Prestamo
    nombre = 'prestamo'
    encabezado = 'Editar préstamo'
    fields = ['libro', 'lector', 'fecha_devolucion', 'estado']

class PrestamoEliminar(EliminarBase):
    model = Prestamo
    nombre = 'prestamo'
    encabezado = 'Eliminar préstamo'