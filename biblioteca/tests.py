from datetime import date, timedelta
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from .models import Libro, Lector, Prestamo


class UsuariosYRolesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_prueba', 'admin@test.com', 'ClaveSegura123!')
        self.biblio = User.objects.create_user('bibliotecario_prueba', password='ClaveSegura123!')
        self.normal = User.objects.create_user('usuario_prueba', email='lector@test.com', password='ClaveSegura123!')
        self.biblio.groups.add(Group.objects.get_or_create(name='Bibliotecario')[0])
        self.normal.groups.add(Group.objects.get_or_create(name='Usuario')[0])
        self.lector = Lector.objects.create(nombre_completo='Lector Prueba', carnet='LC-9991', correo='lector@test.com')
        self.otro_lector = Lector.objects.create(nombre_completo='Otro Lector', carnet='LC-9992', correo='otro@test.com')
        self.libro = Libro.objects.create(titulo='Libro Prueba', autor='Autor Prueba', isbn='9999999999999', cantidad_total=3, cantidad_disponible=3)

    def test_solo_administrador_accede(self):
        for user in (self.normal, self.biblio):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('usuarios_lista')).status_code, 403)
            self.assertEqual(self.client.get(reverse('usuarios_nuevo')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('usuarios_lista')).status_code, 200)

    def test_creacion_sin_privilegios(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('usuarios_nuevo'), {'username':'nuevo','first_name':'Nuevo','last_name':'Lector','email':'otro@test.com','rol':'Usuario','lector':str(self.otro_lector.pk),'password1':'ClaveLarga123!','password2':'ClaveLarga123!','activo':'on'})
        self.assertEqual(respuesta.status_code,302)
        nuevo=User.objects.get(username='nuevo')
        self.assertFalse(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertTrue(nuevo.groups.filter(name='Usuario').exists())

    def test_cambio_de_rol(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('usuarios_editar',args=[self.normal.pk]), {'username':self.normal.username,'first_name':'','last_name':'','email':self.normal.email,'rol':'Bibliotecario','activo':'on'})
        self.assertEqual(respuesta.status_code,302)
        self.normal.refresh_from_db()
        self.assertTrue(self.normal.groups.filter(name='Bibliotecario').exists())
        self.assertFalse(self.normal.is_staff)

    def test_no_quitar_ultimo_administrador(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('usuarios_editar',args=[self.admin.pk]), {'username':self.admin.username,'email':self.admin.email,'rol':'Usuario','activo':'on'})
        self.assertEqual(respuesta.status_code,200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_active)

    def test_usuario_no_accede_a_lectores_ni_creacion_libro(self):
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get(reverse('lector_lista')).status_code,403)
        self.assertEqual(self.client.get(reverse('libro_nuevo')).status_code,403)

    def test_usuario_solo_ve_sus_prestamos(self):
        Prestamo.objects.create(libro=self.libro,lector=self.lector,usuario=self.admin,fecha_devolucion=date.today()+timedelta(days=5))
        Prestamo.objects.create(libro=self.libro,lector=self.otro_lector,usuario=self.admin,fecha_devolucion=date.today()+timedelta(days=5))
        self.client.force_login(self.normal)
        respuesta=self.client.get(reverse('prestamo_lista'))
        self.assertEqual(respuesta.status_code,200)
        self.assertEqual(len(respuesta.context['object_list']),1)
        self.assertEqual(respuesta.context['object_list'][0].lector_id,self.lector.pk)
