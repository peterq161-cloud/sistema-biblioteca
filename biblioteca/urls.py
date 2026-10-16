from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views, usuarios_views, cuentas_views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('cuentas/', cuentas_views.lista, name='cuentas_lista'),
    path('cuentas/nueva/', cuentas_views.nueva, name='cuentas_nueva'),
    path('cuentas/<int:pk>/', cuentas_views.detalle, name='cuentas_detalle'),
    path('cuentas/<int:pk>/editar/', cuentas_views.editar, name='cuentas_editar'),
    path('cuentas/<int:pk>/contrasena/', cuentas_views.contrasena, name='cuentas_contrasena'),
    path('usuarios/', usuarios_views.lista, name='usuarios_lista'),
    path('usuarios/nuevo/', usuarios_views.editar, name='usuarios_nuevo'),
    path('usuarios/<int:pk>/editar/', usuarios_views.editar, name='usuarios_editar'),
    path('usuarios/<int:pk>/eliminar/', usuarios_views.eliminar, name='usuarios_eliminar'),
    path('login/', LoginView.as_view(template_name='login.html',
                                     redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('resumen/', views.resumen, name='resumen'),
    path('libros/buscar/', views.buscar_libros, name='buscar_libros'),
    path('lectores/buscar/', views.buscar_lectores, name='buscar_lectores'),
    path('libros/', views.LibroListaFinal.as_view(), name='libro_lista'),
    path('libros/nuevo/', views.LibroNuevo.as_view(), name='libro_nuevo'),
    path('libros/<int:pk>/editar/', views.LibroEditar.as_view(), name='libro_editar'),
    path('libros/<int:pk>/eliminar/', views.LibroEliminar.as_view(), name='libro_eliminar'),

    path('lectores/', views.LectorListaFinal.as_view(), name='lector_lista'),
    path('lectores/nuevo/', views.LectorNuevo.as_view(), name='lector_nuevo'),
    path('lectores/<int:pk>/editar/', views.LectorEditar.as_view(), name='lector_editar'),
    path('lectores/<int:pk>/eliminar/', views.LectorEliminar.as_view(), name='lector_eliminar'),

    path('prestamos/', views.PrestamoListaFinal.as_view(), name='prestamo_lista'),
    path('prestamos/nuevo/', views.PrestamoNuevo.as_view(), name='prestamo_nuevo'),
    path('prestamos/<int:pk>/editar/', views.PrestamoEditar.as_view(), name='prestamo_editar'),
    path('prestamos/<int:pk>/devolver/', views.PrestamoDevolver.as_view(), name='prestamo_devolver'),
    path('prestamos/<int:pk>/eliminar/', views.PrestamoEliminar.as_view(), name='prestamo_eliminar'),
]
