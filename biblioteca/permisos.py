from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test


def es_admin(user):
    return user.is_authenticated and user.is_active and user.is_superuser


def es_bibliotecario(user):
    return (user.is_authenticated and user.is_active and
            (user.is_superuser or user.groups.filter(name='Bibliotecario').exists()))


def contexto_roles(request):
    return {'es_admin': es_admin(request.user),
            'es_personal': es_bibliotecario(request.user)}


class PersonalMixin(UserPassesTestMixin):
    def test_func(self):
        return es_bibliotecario(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied('No tienes permiso para esta operación.')
        return super().handle_no_permission()


class AdministradorMixin(PersonalMixin):
    def test_func(self):
        return es_admin(self.request.user)


def lector_del_usuario(user):
    """Vincula mediante correo único verificado por el administrador.
    No muestra datos si hay correo vacío o ambiguo.
    """
    from .models import Lector
    if not user.is_authenticated or not user.email:
        return None
    coincidencias = list(Lector.objects.filter(correo__iexact=user.email.strip())[:2])
    return coincidencias[0] if len(coincidencias) == 1 else None
