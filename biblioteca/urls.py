from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views


def crud(nombre, plural, lista, nuevo, editar, eliminar):
    return [
        path(f'{plural}/', lista.as_view(), name=f'{nombre}_lista'),
        path(f'{plural}/nuevo/', nuevo.as_view(), name=f'{nombre}_nuevo'),
        path(f'{plural}/<int:pk>/editar/', editar.as_view(), name=f'{nombre}_editar'),
        path(f'{plural}/<int:pk>/eliminar/', eliminar.as_view(), name=f'{nombre}_eliminar'),
    ]


urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

urlpatterns += crud('libro', 'libros', views.LibroLista, views.LibroNuevo,
                    views.LibroEditar, views.LibroEliminar)
urlpatterns += crud('lector', 'lectores', views.LectorLista, views.LectorNuevo,
                    views.LectorEditar, views.LectorEliminar)
urlpatterns += crud('prestamo', 'prestamos', views.PrestamoLista, views.PrestamoNuevo,
                    views.PrestamoEditar, views.PrestamoEliminar)
                    