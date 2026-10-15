from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.shortcuts import render
from .permisos import es_admin, es_bibliotecario, lector_del_usuario
from .models import Prestamo


@login_required
def perfil(request):
    usuario = request.user
    rol = 'Administrador' if es_admin(usuario) else ('Bibliotecario' if es_bibliotecario(usuario) else 'Usuario')
    lector = lector_del_usuario(usuario) if rol == 'Usuario' else None
    prestamos = Prestamo.objects.filter(lector=lector).select_related('libro').order_by('-pk') if lector else Prestamo.objects.none()
    activos = prestamos.filter(estado='Activo')
    return render(request, 'perfil/detalle.html', {
        'rol_perfil': rol, 'lector_perfil': lector,
        'prestamos_activos_perfil': activos,
        'prestamos_vencidos_perfil': activos.filter(fecha_devolucion__lt=date.today()),
    })


class CambiarContrasena(LoginRequiredMixin, PasswordChangeView):
    template_name = 'perfil/contrasena.html'
    success_url = reverse_lazy('perfil_contrasena_lista')


@login_required
def contrasena_lista(request):
    return render(request, 'perfil/contrasena_lista.html')
