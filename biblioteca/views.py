from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, connection, IntegrityError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from datetime import date
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import LectorForm, LibroForm, PrestamoEditForm, PrestamoForm
from .models import Lector, Libro, Prestamo
from .permisos import PersonalMixin, AdministradorMixin, es_bibliotecario, es_admin, lector_del_usuario
from django.core.exceptions import PermissionDenied
from django.db.models import F


# ---------------------------------------------------------------- Inicio

def datos_inicio(user):
    hoy = date.today()
    personal = es_bibliotecario(user)
    lector = lector_del_usuario(user) if not personal else None
    prestamos = Prestamo.objects.all() if personal else (Prestamo.objects.filter(lector=lector) if lector else Prestamo.objects.none())
    activos = prestamos.filter(estado='Activo')
    vencidos = activos.filter(fecha_devolucion__lt=hoy)
    disponibles = Libro.objects.aggregate(total=Sum('cantidad_total'), disponibles=Sum('cantidad_disponible'))
    return {
        'hoy': hoy, 'es_personal': personal,
        'total_titulos': Libro.objects.count(),
        'ejemplares_total': disponibles['total'] or 0,
        'ejemplares_disponibles': disponibles['disponibles'] or 0,
        'total_lectores': Lector.objects.count() if personal else None,
        'prestamos_activos': activos.count(),
        'prestamos_vencidos': vencidos.count(),
        'prestamos_devueltos': prestamos.filter(estado='Devuelto').count(),
        'libros_agotados': Libro.objects.filter(cantidad_disponible=0).order_by('-fecha_registro')[:5],
        'total_agotados': Libro.objects.filter(cantidad_disponible=0).count(),
        'vencidos': vencidos.select_related('libro', 'lector').order_by('fecha_devolucion')[:5],
        'por_vencer': activos.filter(fecha_devolucion__gte=hoy, fecha_devolucion__lte=hoy + timedelta(days=3)).select_related('libro', 'lector').order_by('fecha_devolucion')[:5],
        'ultimos': prestamos.select_related('libro', 'lector').order_by('-id')[:6],
        'populares': Libro.objects.annotate(veces=Count('prestamo')).filter(veces__gt=0).order_by('-veces', 'titulo')[:5],
    }


@login_required
def inicio(request):
    return render(request, 'inicio.html', datos_inicio(request.user))


@login_required
def resumen(request):
    datos = datos_inicio(request.user)
    def prestamo_json(prestamo):
        return {'libro': prestamo.libro.titulo, 'lector': prestamo.lector.nombre_completo if datos['es_personal'] else '',
                'fecha': prestamo.fecha_devolucion.strftime('%d/%m/%Y') if prestamo.fecha_devolucion else 'Sin fecha',
                'estado': 'Devuelto' if prestamo.estado == 'Devuelto' else ('Vencido' if prestamo.esta_vencido else 'Activo'),
                'dias_retraso': prestamo.dias_retraso}
    return JsonResponse({
        'total_titulos': datos['total_titulos'], 'ejemplares_total': datos['ejemplares_total'],
        'ejemplares_disponibles': datos['ejemplares_disponibles'],
        'total_lectores': datos['total_lectores'] if datos['es_personal'] else None,
        'prestamos_activos': datos['prestamos_activos'], 'prestamos_vencidos': datos['prestamos_vencidos'],
        'prestamos_devueltos': datos['prestamos_devueltos'], 'total_agotados': datos['total_agotados'],
        'vencidos': [prestamo_json(x) for x in datos['vencidos']],
        'por_vencer': [prestamo_json(x) for x in datos['por_vencer']],
        'ultimos': [prestamo_json(x) for x in datos['ultimos']],
        'populares': [{'titulo': x.titulo, 'veces': x.veces} for x in datos['populares']],
        'libros_agotados': [{'titulo': x.titulo, 'isbn': x.isbn} for x in datos['libros_agotados']],
    })


def _buscar_autocomplete(request, modelo):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    if not es_bibliotecario(request.user):
        raise PermissionDenied('Solo el personal puede buscar registros para préstamos.')
    q = request.GET.get('q', '').strip()[:100]
    if not q:
        return JsonResponse({'resultados': []})
    if modelo == 'libro':
        filtro = Q(titulo__icontains=q) | Q(autor__icontains=q) | Q(isbn__icontains=q)
        if q.isdigit(): filtro |= Q(pk=int(q))
        resultados = Libro.objects.filter(filtro).order_by('titulo')[:10]
        return JsonResponse({'resultados': [{'id': x.pk, 'texto': f'{x.titulo} — {x.autor} — {x.isbn} — {x.cantidad_disponible} disponibles' if x.cantidad_disponible else f'{x.titulo} — {x.autor} — {x.isbn} — Agotado', 'deshabilitado': x.cantidad_disponible <= 0} for x in resultados]})
    filtro = Q(nombre_completo__icontains=q) | Q(carnet__icontains=q)
    if q.isdigit(): filtro |= Q(pk=int(q))
    resultados = Lector.objects.filter(filtro).annotate(
        num_activos=Count('prestamo', filter=Q(prestamo__estado='Activo')),
        num_vencidos=Count('prestamo', filter=Q(prestamo__estado='Activo', prestamo__fecha_devolucion__lt=date.today()))
    ).order_by('nombre_completo')[:10]
    return JsonResponse({'resultados': [{'id': x.pk, 'texto': f'{x.nombre_completo} ({x.carnet})' + (' — Préstamo vencido' if x.num_vencidos else (' — Límite de 3 activos' if x.num_activos >= 3 else '')), 'deshabilitado': bool(x.num_vencidos or x.num_activos >= 3)} for x in resultados]})


def buscar_libros(request):
    return _buscar_autocomplete(request, 'libro')


def buscar_lectores(request):
    return _buscar_autocomplete(request, 'lector')


# ---------------------------------------------------------------- Listados

class ListaBase(LoginRequiredMixin, ListView):
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        parametros = self.request.GET.copy()
        parametros.pop('page', None)
        ctx['qs'] = parametros.urlencode()
        ctx['q'] = self.request.GET.get('q', '').strip()
        return ctx


class LibroLista(ListaBase):
    model = Libro
    template_name = 'crud/lista_libros.html'

    def get_queryset(self):
        libros = Libro.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            libros = libros.filter(
                Q(titulo__icontains=q) | Q(autor__icontains=q)
                | Q(isbn__icontains=q) | Q(categoria__icontains=q) | (Q(pk=int(q)) if q.isdigit() else Q()))
        if self.request.GET.get('disp') == 'si':
            libros = libros.filter(cantidad_disponible__gt=0)
        elif self.request.GET.get('disp') == 'no':
            libros = libros.filter(cantidad_disponible=0)
        orden = self.request.GET.get('orden', 'reciente')
        return libros.order_by({'antiguo': 'fecha_registro', 'az': 'titulo', 'disponibilidad': '-cantidad_disponible'}.get(orden, '-fecha_registro'), '-pk')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['disp'] = self.request.GET.get('disp', '')
        return ctx


class LectorLista(PersonalMixin, ListaBase):
    model = Lector
    template_name = 'crud/lista_lectores.html'

    def get_queryset(self):
        lectores = (Lector.objects
                    .annotate(activos=Count('prestamo', filter=Q(prestamo__estado='Activo'))))
        q = self.request.GET.get('q', '').strip()
        if q:
            lectores = lectores.filter(
                Q(nombre_completo__icontains=q) | Q(carnet__icontains=q)
                | Q(correo__icontains=q) | Q(telefono__icontains=q) | (Q(pk=int(q)) if q.isdigit() else Q(pk__isnull=True)))
        filtro = self.request.GET.get('filtro')
        if filtro == 'activos':
            lectores = lectores.filter(prestamo__estado='Activo').distinct()
        elif filtro == 'vencidos':
            lectores = lectores.filter(prestamo__estado='Activo', prestamo__fecha_devolucion__lt=date.today()).distinct()
        orden = self.request.GET.get('orden', 'reciente')
        return lectores.order_by({'antiguo':'fecha_registro','az':'nombre_completo','disponibilidad':'-activos'}.get(orden,'-fecha_registro'), '-pk')


class PrestamoLista(ListaBase):
    model = Prestamo
    template_name = 'crud/lista_prestamos.html'

    def get_queryset(self):
        prestamos = Prestamo.objects.select_related('libro', 'lector', 'usuario')
        if not es_bibliotecario(self.request.user):
            lector = lector_del_usuario(self.request.user)
            prestamos = prestamos.filter(lector=lector) if lector else prestamos.none()
        q = self.request.GET.get('q', '').strip()
        if q:
            prestamos = prestamos.filter(
                Q(libro__titulo__icontains=q) | Q(lector__nombre_completo__icontains=q)
                | Q(lector__carnet__icontains=q) | Q(libro__isbn__icontains=q) | (Q(pk=int(q)) if q.isdigit() else Q()))
        estado = self.request.GET.get('estado', '')
        if estado == 'activo':
            prestamos = prestamos.filter(estado='Activo', fecha_devolucion__gte=date.today())
        elif estado == 'devuelto':
            prestamos = prestamos.filter(estado='Devuelto')
        elif estado == 'vencido':
            prestamos = prestamos.filter(estado='Activo',
                                         fecha_devolucion__lt=date.today())
        orden = self.request.GET.get('orden', 'reciente')
        return prestamos.order_by({'antiguo':'id', 'az':'libro__titulo', 'disponibilidad':'fecha_devolucion'}.get(orden,'-id'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado'] = self.request.GET.get('estado', '')
        ctx['hoy'] = date.today()
        base = Prestamo.objects.all()
        if not es_bibliotecario(self.request.user):
            lector = lector_del_usuario(self.request.user)
            base = base.filter(lector=lector) if lector else base.none()
        ctx['conteos'] = {'todos':base.count(), 'activo':base.filter(estado='Activo', fecha_devolucion__gte=date.today()).count(), 'vencido':base.filter(estado='Activo', fecha_devolucion__lt=date.today()).count(), 'devuelto':base.filter(estado='Devuelto').count()}
        return ctx


# ---------------------------------------------------------------- Crear y editar

class FormBase(LoginRequiredMixin):
    template_name = 'crud/form.html'
    encabezado = ''
    url_lista = ''
    mensaje_ok = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['encabezado'] = self.encabezado
        ctx['url_lista'] = self.url_lista
        return ctx

    def get_success_url(self):
        return reverse(self.url_lista)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, self.mensaje_ok)
        return respuesta


class LibroNuevo(PersonalMixin, FormBase, CreateView):
    model = Libro
    form_class = LibroForm
    url_lista = 'libro_lista'
    encabezado = 'Registrar libro'
    mensaje_ok = 'Libro registrado.'


class LibroEditar(PersonalMixin, FormBase, UpdateView):
    model = Libro
    form_class = LibroForm
    url_lista = 'libro_lista'
    encabezado = 'Editar libro'
    mensaje_ok = 'Libro actualizado.'


class LectorNuevo(PersonalMixin, FormBase, CreateView):
    model = Lector
    form_class = LectorForm
    url_lista = 'lector_lista'
    encabezado = 'Registrar lector'
    mensaje_ok = 'Lector registrado.'

    def form_valid(self, form):
        # PostgreSQL: bloqueo transaccional global para asignar carnets sin carreras.
        with transaction.atomic():
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_xact_lock(%s)', [741852963])
            maximo = 0
            for carnet in Lector.objects.filter(carnet__startswith='LC-').values_list('carnet', flat=True):
                if carnet[3:].isdigit():
                    maximo = max(maximo, int(carnet[3:]))
            form.instance.carnet = f'LC-{maximo + 1:04d}'
            return super().form_valid(form)



class LectorEditar(PersonalMixin, FormBase, UpdateView):
    model = Lector
    form_class = LectorForm
    url_lista = 'lector_lista'
    encabezado = 'Editar lector'
    mensaje_ok = 'Lector actualizado.'


class PrestamoNuevo(PersonalMixin, FormBase, CreateView):
    model = Prestamo
    form_class = PrestamoForm
    url_lista = 'prestamo_lista'
    encabezado = 'Registrar préstamo'

    def form_valid(self, form):
        with transaction.atomic():
            # Bloquea la fila del libro para que dos préstamos simultáneos
            # no se lleven el mismo último ejemplar.
            libro = Libro.objects.select_for_update().get(pk=form.cleaned_data['libro'].pk)
            if libro.cantidad_disponible < 1:
                form.add_error('libro', 'No quedan ejemplares disponibles de este libro.')
                return self.form_invalid(form)
            lector = form.cleaned_data['lector']
            activos = Prestamo.objects.filter(lector=lector, estado='Activo')
            if activos.filter(fecha_devolucion__lt=date.today()).exists() or activos.count() >= 3 or activos.filter(libro=libro).exists():
                form.add_error('lector', 'Préstamo no permitido: hay un vencimiento, 3 préstamos activos o un préstamo duplicado.')
                return self.form_invalid(form)
            prestamo = form.save(commit=False)
            prestamo.usuario = self.request.user
            prestamo.estado = 'Activo'
            prestamo.save()
            libro.cantidad_disponible -= 1
            libro.estado = 'Disponible' if libro.cantidad_disponible > 0 else 'Agotado'
            libro.save(update_fields=['cantidad_disponible', 'estado'])
        messages.success(
            self.request, f'Préstamo registrado: «{libro.titulo}» para {prestamo.lector}.')
        return redirect(self.get_success_url())


class PrestamoEditar(PersonalMixin, FormBase, UpdateView):
    model = Prestamo
    form_class = PrestamoEditForm
    url_lista = 'prestamo_lista'
    encabezado = 'Cambiar fecha límite'
    mensaje_ok = 'Fecha límite actualizada.'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        prestamo = get_object_or_404(Prestamo, pk=kwargs['pk'])
        if prestamo.estado != 'Activo':
            messages.warning(request, 'Un préstamo devuelto ya no se puede modificar.')
            return redirect('prestamo_lista')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['resumen'] = f'{self.object.libro} — {self.object.lector}'
        return ctx


# ---------------------------------------------------------------- Devolver

class PrestamoDevolver(PersonalMixin, LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        with transaction.atomic():
            prestamo = get_object_or_404(Prestamo.objects.select_for_update(), pk=pk)
            if prestamo.estado != 'Activo':
                messages.info(request, 'Ese préstamo ya estaba devuelto.')
                return redirect('prestamo_lista')
            libro = Libro.objects.select_for_update().get(pk=prestamo.libro_id)
            prestamo.estado = 'Devuelto'
            prestamo.fecha_devolucion = date.today()
            prestamo.save(update_fields=['estado', 'fecha_devolucion'])
            libro.cantidad_disponible = min(libro.cantidad_total,
                                            libro.cantidad_disponible + 1)
            libro.estado = 'Disponible'
            libro.save(update_fields=['cantidad_disponible', 'estado'])
        messages.success(request, f'Devolución registrada: «{libro.titulo}».')
        return redirect('prestamo_lista')


# ---------------------------------------------------------------- Eliminar

class EliminarBase(LoginRequiredMixin, DeleteView):
    template_name = 'crud/eliminar.html'
    encabezado = ''
    url_lista = ''
    aviso = ''

    def bloqueo(self, objeto):
        """Devuelve un texto si el registro no se puede eliminar."""
        return ''

    def borrar(self, objeto):
        objeto.delete()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['encabezado'] = self.encabezado
        ctx['url_lista'] = self.url_lista
        ctx['aviso'] = self.aviso
        ctx['bloqueo'] = self.bloqueo(self.object)
        return ctx

    def get_success_url(self):
        return reverse(self.url_lista)

    def form_valid(self, form):
        razon = self.bloqueo(self.object)
        if razon:
            messages.error(self.request, razon)
            return redirect(self.get_success_url())
        nombre = str(self.object)
        self.borrar(self.object)
        messages.success(self.request, f'«{nombre}» eliminado.')
        return redirect(self.get_success_url())


class LibroEliminar(AdministradorMixin, EliminarBase):
    model = Libro
    url_lista = 'libro_lista'
    encabezado = 'Eliminar libro'

    def bloqueo(self, libro):
        if libro.prestamo_set.filter(estado='Activo').exists():
            return 'Este libro tiene préstamos activos; deben devolverse primero.'
        if libro.prestamo_set.exists():
            return 'No se puede eliminar un libro que tiene préstamos en su historial.'
        return ''


class LectorEliminar(AdministradorMixin, EliminarBase):
    model = Lector
    url_lista = 'lector_lista'
    encabezado = 'Eliminar lector'

    def bloqueo(self, lector):
        if lector.prestamo_set.filter(estado='Activo').exists():
            return 'Este lector tiene préstamos activos; deben devolverse primero.'
        if lector.prestamo_set.exists():
            return 'No se puede eliminar un lector que tiene préstamos en su historial.'
        return ''


class PrestamoEliminar(AdministradorMixin, EliminarBase):
    model = Prestamo
    url_lista = 'prestamo_lista'
    encabezado = 'Eliminar préstamo'
    aviso = 'Si el préstamo sigue activo, el ejemplar vuelve al inventario.'

    def borrar(self, prestamo):
        with transaction.atomic():
            if prestamo.estado == 'Activo':
                libro = Libro.objects.select_for_update().get(pk=prestamo.libro_id)
                libro.cantidad_disponible = min(libro.cantidad_total,
                                                libro.cantidad_disponible + 1)
                libro.estado = 'Disponible'
                libro.save(update_fields=['cantidad_disponible', 'estado'])
            prestamo.delete()



# Contexto explícito para la plantilla compartida; sin modificaciones dinámicas de clases.
class ListaPlantillaMixin:
    template_name = 'crud/lista.html'
    columnas = ()
    encabezado = ''
    url_lista = ''
    url_nuevo = ''
    url_editar = ''
    url_eliminar = ''

    def valores(self, obj):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(encabezado=self.encabezado, columnas=self.columnas,
                   filas=[(o, self.valores(o)) for o in ctx['object_list']],
                   url_lista=self.url_lista, url_nuevo=self.url_nuevo,
                   url_editar=self.url_editar, url_eliminar=self.url_eliminar,
                   puede_editar=es_bibliotecario(self.request.user),
                   puede_eliminar=es_admin(self.request.user),
                   orden=self.request.GET.get('orden', 'reciente'))
        return ctx


class LibroListaFinal(ListaPlantillaMixin, LibroLista):
    columnas = ('Título', 'Autor', 'ISBN', 'Disponibles', 'Estado')
    encabezado = 'Libros'
    url_lista, url_nuevo, url_editar, url_eliminar = 'libro_lista', 'libro_nuevo', 'libro_editar', 'libro_eliminar'

    def valores(self, o):
        return [o.titulo, o.autor, o.isbn, o.cantidad_disponible, o.estado]


class LectorListaFinal(ListaPlantillaMixin, LectorLista):
    columnas = ('Nombre', 'Carnet', 'Correo', 'Teléfono')
    encabezado = 'Lectores'
    url_lista, url_nuevo, url_editar, url_eliminar = 'lector_lista', 'lector_nuevo', 'lector_editar', 'lector_eliminar'

    def valores(self, o):
        return [o.nombre_completo, o.carnet, o.correo, o.telefono]


class PrestamoListaFinal(ListaPlantillaMixin, PrestamoLista):
    columnas = ('Libro', 'Lector', 'Carnet', 'Fecha límite / devolución', 'Estado')
    encabezado = 'Préstamos'
    url_lista, url_nuevo, url_editar, url_eliminar = 'prestamo_lista', 'prestamo_nuevo', 'prestamo_editar', 'prestamo_eliminar'

    def valores(self, o):
        estado = 'Devuelto' if o.estado == 'Devuelto' else (f'Vencido ({o.dias_retraso} días)' if o.esta_vencido else 'Activo')
        return [o.libro.titulo, o.lector.nombre_completo, o.lector.carnet, o.fecha_devolucion, estado]
