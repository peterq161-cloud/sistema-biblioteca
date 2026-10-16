from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from .permisos import es_admin
from .usuarios_forms import UsuarioForm


def solo_admin(view):
    @login_required
    def wrapper(request,*args,**kwargs):
        if not es_admin(request.user):raise PermissionDenied('Solo el Administrador puede gestionar usuarios y roles.')
        return view(request,*args,**kwargs)
    return wrapper


def personal():
    """Cuentas que se gestionan aquí: Administradores y Bibliotecarios (no estudiantes)."""
    return User.objects.filter(Q(is_superuser=True)|Q(groups__name='Bibliotecario')).distinct()


def rol_de(user):
    return 'Administrador' if user.is_superuser else ('Bibliotecario' if user.groups.filter(name='Bibliotecario').exists() else 'Usuario')


@solo_admin
def lista(request):
    usuarios=personal().prefetch_related('groups')
    q=request.GET.get('q','').strip()[:100]; rol=request.GET.get('rol',''); estado=request.GET.get('estado','')
    if q:usuarios=usuarios.filter(Q(username__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(email__icontains=q))
    if rol=='Administrador':usuarios=usuarios.filter(is_superuser=True)
    elif rol=='Bibliotecario':usuarios=usuarios.filter(is_superuser=False,groups__name='Bibliotecario')
    if estado in ('activo','inactivo'):usuarios=usuarios.filter(is_active=(estado=='activo'))
    orden=request.GET.get('orden','reciente')
    usuarios=usuarios.order_by('date_joined' if orden=='antiguo' else 'username' if orden=='az' else '-date_joined','-pk').distinct()
    pagina=Paginator(usuarios,10).get_page(request.GET.get('page'))
    from .models import Lector
    correos=[u.email for u in pagina.object_list if u.email]
    lectores={x.correo.lower():x for x in Lector.objects.filter(correo__in=correos) if x.correo}
    filas=[{'obj':u,'rol':rol_de(u),'lector':lectores.get(u.email.lower()) if u.email else None} for u in pagina.object_list]
    params=request.GET.copy();params.pop('page',None)
    return render(request,'usuarios/lista.html',{'filas':filas,'pagina':pagina,'qs':params.urlencode(),'rol':rol,'estado':estado,'orden':orden})


@solo_admin
@require_http_methods(['GET','POST'])
def editar(request,pk=None):
    usuario=get_object_or_404(personal(),pk=pk) if pk else None
    form=UsuarioForm(request.POST or None,instance=usuario)
    if request.method=='POST' and form.is_valid():
        nuevo_rol=form.cleaned_data['rol']
        if usuario and usuario.pk==request.user.pk and (nuevo_rol!='Administrador' or not form.cleaned_data['activo']):
            form.add_error(None,'No puedes quitarte el rol de Administrador ni desactivar tu propia cuenta.')
        elif usuario and usuario.is_superuser and nuevo_rol!='Administrador' and not User.objects.filter(is_superuser=True,is_active=True).exclude(pk=usuario.pk).exists():
            form.add_error(None,'No puedes quitar el último Administrador activo del sistema.')
        elif usuario and usuario.is_superuser and not form.cleaned_data['activo'] and not User.objects.filter(is_superuser=True,is_active=True).exclude(pk=usuario.pk).exists():
            form.add_error(None,'No puedes desactivar el último Administrador activo.')
        else:
            with transaction.atomic():
                u=form.save(commit=False)
                u.is_active=form.cleaned_data['activo']
                u.is_superuser=nuevo_rol=='Administrador'
                u.is_staff=nuevo_rol=='Administrador'
                if form.cleaned_data.get('password1'):u.set_password(form.cleaned_data['password1'])
                u.save()
                u.groups.clear()
                if nuevo_rol!='Administrador':
                    grupo,_=Group.objects.get_or_create(name=nuevo_rol)
                    u.groups.add(grupo)
                # No se guardan campos adicionales: el lector se vincula mediante el correo.
            messages.success(request,'Usuario guardado correctamente con el rol '+nuevo_rol+'.')
            return redirect('usuarios_lista')
    return render(request,'usuarios/form.html',{'form':form,'editando':bool(usuario),'usuario_editado':usuario})


@solo_admin
@require_http_methods(['GET','POST'])
def eliminar(request,pk):
    usuario=get_object_or_404(personal(),pk=pk)
    if usuario.pk==request.user.pk:
        messages.error(request,'No puedes eliminar tu propia cuenta de Administrador.')
        return redirect('usuarios_lista')
    if request.method=='POST':
        nombre=usuario.get_full_name() or usuario.username
        try:
            with transaction.atomic():
                usuario.delete()
        except ProtectedError:
            messages.error(request,'No se puede eliminar a '+nombre+' porque registró préstamos. Desactiva la cuenta en su lugar.')
        else:
            messages.success(request,'Usuario '+nombre+' eliminado correctamente.')
        return redirect('usuarios_lista')
    return render(request,'usuarios/eliminar.html',{'objeto':usuario,'rol':rol_de(usuario)})
