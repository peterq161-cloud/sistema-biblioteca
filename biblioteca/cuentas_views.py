from datetime import date
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods
from .models import Lector, Prestamo
from .permisos import es_bibliotecario
from .cuentas_forms import CuentaForm, CuentaPasswordForm

def personal(view):
    @wraps(view)
    @login_required
    def wrapped(request,*args,**kwargs):
        if not es_bibliotecario(request.user):raise PermissionDenied('Solo el personal autorizado puede gestionar cuentas.')
        return view(request,*args,**kwargs)
    return wrapped

def cuentas_permitidas():
    return User.objects.filter(is_superuser=False,is_staff=False).exclude(groups__name='Bibliotecario').distinct()

def cuenta_objetivo(pk):
    return get_object_or_404(cuentas_permitidas(),pk=pk)

def resumen_cuentas(usuarios):
    """Resuelve vínculos y conteos en dos consultas para la página completa."""
    emails={u.email.casefold() for u in usuarios if u.email}
    lectores=list(Lector.objects.all()) if emails else []
    por_correo={};repetidos=set()
    for l in lectores:
        key=l.correo.strip().casefold() if l.correo else ''
        if key in emails:
            if key in por_correo:repetidos.add(key)
            else:por_correo[key]=l
    for k in repetidos:por_correo.pop(k,None)
    ids=[l.pk for l in por_correo.values()]
    contadores={r['lector_id']:r for r in Prestamo.objects.filter(lector_id__in=ids).values('lector_id').annotate(
        activos=Count('pk',filter=Q(estado='Activo')),
        vencidos=Count('pk',filter=Q(estado='Activo',fecha_devolucion__lt=date.today())),
        devueltos=Count('pk',filter=Q(estado='Devuelto')))}
    resultado=[]
    for u in usuarios:
        lector=por_correo.get(u.email.casefold()) if u.email else None
        nums=contadores.get(lector.pk,{}) if lector else {}
        resultado.append({'obj':u,'lector':lector,'activos':nums.get('activos',0),'vencidos':nums.get('vencidos',0),'devueltos':nums.get('devueltos',0)})
    return resultado

def _correos(qs):
    """Correos de lectores en minusculas, para comparar con User.email sin importar mayusculas."""
    return {c.strip().lower() for c in qs.exclude(correo='').values_list('correo',flat=True) if c and c.strip()}

@personal
def lista(request):
    usuarios=cuentas_permitidas().annotate(email_l=Lower('email'))
    q=request.GET.get('q','').strip()[:100]
    if q:
        emails=_correos(Lector.objects.filter(carnet__icontains=q))
        usuarios=usuarios.filter(Q(username__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(email__icontains=q)|Q(email_l__in=emails))
    estado=request.GET.get('estado','')
    if estado in ('activo','inactivo'):usuarios=usuarios.filter(is_active=(estado=='activo'))
    situacion=request.GET.get('situacion','')
    if situacion:
        hoy=date.today()
        if situacion=='sin_lector':
            usuarios=usuarios.exclude(email_l__in=_correos(Lector.objects.all()))
        elif situacion in ('activos','vencidos','sin_prestamos'):
            prestamos=Prestamo.objects.filter(estado='Activo')
            if situacion=='vencidos':prestamos=prestamos.filter(fecha_devolucion__lt=hoy)
            emails=_correos(Lector.objects.filter(pk__in=prestamos.values('lector_id')))
            if situacion=='sin_prestamos':usuarios=usuarios.exclude(email_l__in=emails)
            else:usuarios=usuarios.filter(email_l__in=emails)
    orden=request.GET.get('orden','reciente')
    usuarios=usuarios.order_by({'antiguo':'date_joined','az':'username'}.get(orden,'-date_joined'),'-pk')
    pagina=Paginator(usuarios,10).get_page(request.GET.get('page'))
    params=request.GET.copy();params.pop('page',None)
    return render(request,'cuentas/lista.html',{'filas':resumen_cuentas(list(pagina.object_list)),'pagina':pagina,'qs':params.urlencode(),'estado':estado,'situacion':situacion,'orden':orden})

@personal
def detalle(request,pk):
    cuenta=cuenta_objetivo(pk)
    fila=resumen_cuentas([cuenta])[0]
    prestamos=Prestamo.objects.filter(lector=fila['lector']).select_related('libro').order_by('-pk') if fila['lector'] else Prestamo.objects.none()
    return render(request,'cuentas/detalle.html',{'fila':fila,'prestamos':prestamos})

@personal
@require_http_methods(['GET','POST'])
def nueva(request):
    form=CuentaForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            cuenta=form.save(commit=False)
            cuenta.is_superuser=False;cuenta.is_staff=False;cuenta.is_active=form.cleaned_data['activo']
            cuenta.set_password(form.cleaned_data['password1']);cuenta.save()
            cuenta.groups.set([Group.objects.get_or_create(name='Usuario')[0]])
        messages.success(request,'Cuenta de usuario creada correctamente.')
        return redirect('cuentas_lista')
    return render(request,'cuentas/form.html',{'form':form,'creando':True})

@personal
@require_http_methods(['GET','POST'])
def editar(request,pk):
    cuenta=cuenta_objetivo(pk)
    form=CuentaForm(request.POST or None,instance=cuenta)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            # No se permite editar rol, grupos, permisos ni nombre de usuario.
            cuenta.first_name=form.cleaned_data['first_name'];cuenta.last_name=form.cleaned_data['last_name']
            cuenta.email=form.cleaned_data['email'];cuenta.is_active=form.cleaned_data['activo']
            cuenta.save(update_fields=['first_name','last_name','email','is_active'])
        messages.success(request,'Cuenta actualizada correctamente.')
        return redirect('cuentas_detalle',pk=cuenta.pk)
    return render(request,'cuentas/form.html',{'form':form,'creando':False,'cuenta':cuenta})

@personal
@require_http_methods(['GET','POST'])
def contrasena(request,pk):
    cuenta=cuenta_objetivo(pk)
    form=CuentaPasswordForm(request.POST or None,usuario=cuenta)
    if request.method=='POST' and form.is_valid():
        cuenta.set_password(form.cleaned_data['password1']);cuenta.save(update_fields=['password'])
        messages.success(request,'Contraseña actualizada correctamente.')
        return redirect('cuentas_detalle',pk=cuenta.pk)
    return render(request,'cuentas/contrasena.html',{'form':form,'cuenta':cuenta})
