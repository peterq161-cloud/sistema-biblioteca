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
        respuesta=self.client.post(reverse('usuarios_nuevo'), {'username':'nuevo','first_name':'Nuevo','last_name':'Biblio','email':'biblio-nuevo@test.com','rol':'Bibliotecario','password1':'ClaveLarga123!','password2':'ClaveLarga123!','activo':'on'})
        self.assertEqual(respuesta.status_code,302)
        nuevo=User.objects.get(username='nuevo')
        self.assertFalse(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertTrue(nuevo.groups.filter(name='Bibliotecario').exists())

    def test_cambio_de_rol(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('usuarios_editar',args=[self.biblio.pk]), {'username':self.biblio.username,'first_name':'','last_name':'','email':'','rol':'Administrador','activo':'on'})
        self.assertEqual(respuesta.status_code,302)
        self.biblio.refresh_from_db()
        self.assertTrue(self.biblio.is_superuser)
        self.assertFalse(self.biblio.groups.exists())

    def test_no_quitar_ultimo_administrador(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('usuarios_editar',args=[self.admin.pk]), {'username':self.admin.username,'email':self.admin.email,'rol':'Bibliotecario','activo':'on'})
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


class CuentasUsuariosTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('admin_cuentas','admincuentas@test.com','ClaveSegura123!')
        self.biblio=User.objects.create_user('biblio_cuentas',password='ClaveSegura123!')
        self.biblio.groups.add(Group.objects.get_or_create(name='Bibliotecario')[0])
        self.lector=Lector.objects.create(nombre_completo='Cuenta Lector',carnet='LC-5001',correo='cuenta@test.com')
        self.normal=User.objects.create_user('normal_cuentas',email='cuenta@test.com',password='ClaveSegura123!')
        self.normal.groups.add(Group.objects.get_or_create(name='Usuario')[0])
        self.libro=Libro.objects.create(titulo='Prueba Cuentas',autor='Autor',isbn='ISBN-CUENTAS',cantidad_total=5,cantidad_disponible=5)
    def test_accesos(self):
        for user in (self.admin,self.biblio):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('cuentas_lista')).status_code,200)
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get(reverse('cuentas_lista')).status_code,403)
        self.client.force_login(self.biblio)
        self.assertEqual(self.client.get(reverse('usuarios_lista')).status_code,403)
    def test_creacion_ignora_rol_inyectado(self):
        self.client.force_login(self.biblio)
        Lector.objects.create(nombre_completo='Nuevo Lector',carnet='LC-5002',correo='nuevo-cuenta@test.com')
        respuesta=self.client.post(reverse('cuentas_nueva'),{'username':'nuevo_cuentas','first_name':'Nuevo','last_name':'Lector','email':'nuevo-cuenta@test.com','rol':'Administrador','is_superuser':'on','is_staff':'on','password1':'ClaveSegura123!','password2':'ClaveSegura123!','activo':'on'})
        self.assertEqual(respuesta.status_code,302)
        u=User.objects.get(username='nuevo_cuentas')
        self.assertFalse(u.is_staff);self.assertFalse(u.is_superuser)
        self.assertTrue(u.groups.filter(name='Usuario').exists())
    def test_no_tocar_personal(self):
        self.client.force_login(self.biblio)
        for user in (self.admin,self.biblio):
            for name in ('cuentas_detalle','cuentas_editar','cuentas_contrasena'):
                self.assertIn(self.client.get(reverse(name,args=[user.pk])).status_code,(403,404))
    def test_cambio_contrasena(self):
        self.client.force_login(self.biblio)
        r=self.client.post(reverse('cuentas_contrasena',args=[self.normal.pk]),{'password1':'NuevaClave123!','password2':'NuevaClave123!'})
        self.assertEqual(r.status_code,302)
        self.normal.refresh_from_db();self.assertTrue(self.normal.check_password('NuevaClave123!'))
    def test_listado_solo_usuarios(self):
        self.client.force_login(self.biblio)
        r=self.client.get(reverse('cuentas_lista'))
        ids=[f['obj'].pk for f in r.context['filas']]
        self.assertIn(self.normal.pk,ids);self.assertNotIn(self.admin.pk,ids);self.assertNotIn(self.biblio.pk,ids)
    def test_conteos_busqueda_y_filtros(self):
        from .cuentas_views import resumen_cuentas
        Prestamo.objects.create(libro=self.libro,lector=self.lector,usuario=self.admin,fecha_devolucion=date.today()+timedelta(days=5))
        Prestamo.objects.create(libro=self.libro,lector=self.lector,usuario=self.admin,fecha_devolucion=date.today()-timedelta(days=2))
        Prestamo.objects.create(libro=self.libro,lector=self.lector,usuario=self.admin,fecha_devolucion=date.today(),estado='Devuelto')
        fila=resumen_cuentas([self.normal])[0]
        self.assertEqual((fila['activos'],fila['vencidos'],fila['devueltos']),(2,1,1))
        self.client.force_login(self.biblio)
        for query in ({'q':'LC-5001'},{'situacion':'activos'},{'situacion':'vencidos'}):
            r=self.client.get(reverse('cuentas_lista'),query)
            self.assertEqual(r.status_code,200)
            self.assertIn(self.normal.pk,[f['obj'].pk for f in r.context['filas']])

    def test_staff_no_bibliotecario_no_aparece_ni_se_edita(self):
        extra=User.objects.create_user('staff_extra',email='extra@test.com',password='ClaveSegura123!',is_staff=True)
        self.client.force_login(self.biblio)
        ids=[f['obj'].pk for f in self.client.get(reverse('cuentas_lista')).context['filas']]
        self.assertNotIn(extra.pk,ids)
        self.assertIn(self.client.get(reverse('cuentas_contrasena',args=[extra.pk])).status_code,(403,404))

    def test_filtros_ignoran_mayusculas_en_correo(self):
        self.lector.correo='Cuenta@Test.com';self.lector.save()
        Prestamo.objects.create(libro=self.libro,lector=self.lector,usuario=self.admin,fecha_devolucion=date.today()-timedelta(days=3))
        self.client.force_login(self.biblio)
        for query in ({'q':'LC-5001'},{'situacion':'activos'},{'situacion':'vencidos'}):
            ids=[f['obj'].pk for f in self.client.get(reverse('cuentas_lista'),query).context['filas']]
            self.assertIn(self.normal.pk,ids,query)
        ids=[f['obj'].pk for f in self.client.get(reverse('cuentas_lista'),{'situacion':'sin_prestamos'}).context['filas']]
        self.assertNotIn(self.normal.pk,ids)
        ids=[f['obj'].pk for f in self.client.get(reverse('cuentas_lista'),{'situacion':'sin_lector'}).context['filas']]
        self.assertNotIn(self.normal.pk,ids)

    def test_edicion_no_cambia_rol_ni_usuario(self):
        self.client.force_login(self.biblio)
        r=self.client.post(reverse('cuentas_editar',args=[self.normal.pk]),{'first_name':'Ana','last_name':'Gomez','email':'cuenta@test.com','lector':str(self.lector.pk),'activo':'on','username':'hack','rol':'Administrador','is_superuser':'on'})
        self.assertEqual(r.status_code,302)
        self.normal.refresh_from_db()
        self.assertEqual(self.normal.username,'normal_cuentas');self.assertEqual(self.normal.first_name,'Ana')
        self.assertFalse(self.normal.is_superuser);self.assertFalse(self.normal.is_staff)
        self.assertTrue(self.normal.groups.filter(name='Usuario').exists())

    def test_menu_segun_rol_y_cerrar_sesion(self):
        self.client.force_login(self.biblio)
        html=self.client.get(reverse('inicio')).content.decode()
        self.assertIn('Cuentas de usuarios',html);self.assertNotIn('Usuarios y roles',html)
        self.assertIn('side-logout',html);self.assertNotIn('desktopMenuToggle',html)
        self.client.force_login(self.admin)
        html=self.client.get(reverse('inicio')).content.decode()
        self.assertIn('Cuentas de usuarios',html);self.assertIn('Usuarios y roles',html)
        self.client.force_login(self.normal)
        html=self.client.get(reverse('inicio')).content.decode()
        self.assertNotIn('Cuentas de usuarios',html)


class EliminarUsuarioTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('adm_del','a@t.com','Clave-Segura-1')
        self.otro=User.objects.create_user('otro_del',password='Clave-Segura-1')
        self.otro.groups.add(Group.objects.get_or_create(name='Bibliotecario')[0])
        self.biblio=User.objects.create_user('bib_del',password='Clave-Segura-1')
        g,_=Group.objects.get_or_create(name='Bibliotecario');self.biblio.groups.add(g)

    def test_admin_elimina_otro_usuario(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('usuarios_eliminar',args=[self.otro.pk])).status_code,200)
        r=self.client.post(reverse('usuarios_eliminar',args=[self.otro.pk]))
        self.assertEqual(r.status_code,302)
        self.assertFalse(User.objects.filter(pk=self.otro.pk).exists())

    def test_admin_no_puede_eliminarse_a_si_mismo(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios_eliminar',args=[self.admin.pk]))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        html=self.client.get(reverse('usuarios_lista')).content.decode()
        self.assertNotIn(reverse('usuarios_eliminar',args=[self.admin.pk]),html)
        self.assertIn(reverse('usuarios_eliminar',args=[self.otro.pk]),html)

    def test_bibliotecario_y_usuario_no_pueden_eliminar(self):
        for u in (self.biblio,self.otro):
            self.client.force_login(u)
            r=self.client.post(reverse('usuarios_eliminar',args=[self.biblio.pk if u!=self.biblio else self.otro.pk]))
            self.assertEqual(r.status_code,403)
        self.assertTrue(User.objects.filter(pk=self.otro.pk).exists())

    def test_no_elimina_usuario_con_prestamos(self):
        libro=Libro.objects.create(titulo='L',autor='A',isbn='9780000000001',cantidad_total=1,cantidad_disponible=1)
        lector=Lector.objects.create(nombre_completo='Lec',carnet='LC-7777',correo='lec@t.com')
        Prestamo.objects.create(libro=libro,lector=lector,usuario=self.otro,fecha_devolucion=date.today()+timedelta(days=5))
        self.client.force_login(self.admin)
        r=self.client.post(reverse('usuarios_eliminar',args=[self.otro.pk]),follow=True)
        self.assertEqual(r.status_code,200)
        self.assertTrue(User.objects.filter(pk=self.otro.pk).exists())
        self.assertContains(r,'registró préstamos')


class CrearCuentasLectoresTests(TestCase):
    def test_crea_cuentas_para_lectores_sin_cuenta(self):
        from django.core.management import call_command
        from io import StringIO
        Lector.objects.create(nombre_completo='Ana Martínez Peña', carnet='LC-5001', correo='Ana.Martinez@example.com')
        Lector.objects.create(nombre_completo='Luis Gómez', carnet='LC-5002', correo='luis@example.com')
        Lector.objects.create(nombre_completo='Sin Correo', carnet='LC-5003', correo='')
        User.objects.create_user('existente', email='LUIS@example.com', password='x')
        out=StringIO()
        call_command('crear_cuentas_lectores','--password','Biblio2026x',stdout=out)
        ana=User.objects.get(email='ana.martinez@example.com')
        self.assertEqual(ana.username,'ana.martinez');self.assertEqual(ana.first_name,'Ana');self.assertEqual(ana.last_name,'Martínez Peña')
        self.assertTrue(ana.check_password('Biblio2026x'));self.assertFalse(ana.is_staff);self.assertFalse(ana.is_superuser)
        self.assertTrue(ana.groups.filter(name='Usuario').exists())
        self.assertEqual(User.objects.filter(email__iexact='luis@example.com').count(),1)
        self.assertEqual(User.objects.count(),2)
        call_command('crear_cuentas_lectores','--password','Biblio2026x',stdout=StringIO())
        self.assertEqual(User.objects.count(),2)


class CuentaFormLectorTests(TestCase):
    def test_opciones_de_lector_incluyen_carnet(self):
        from .cuentas_forms import CuentaForm
        Lector.objects.create(nombre_completo='Sofía Castillo', carnet='LC-1005', correo='s@example.com')
        textos=[l for _,l in CuentaForm().fields['lector'].choices]
        self.assertIn('Sofía Castillo (LC-1005)',textos)


class UsuariosYRolesSoloPersonalTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('adm_sp','adm@t.com','Clave-Segura-1')
        self.biblio=User.objects.create_user('bib_sp',email='bib@t.com',password='Clave-Segura-1')
        self.biblio.groups.add(Group.objects.get_or_create(name='Bibliotecario')[0])
        self.estudiante=User.objects.create_user('estu_sp',email='estu@t.com',password='Clave-Segura-1')
        self.estudiante.groups.add(Group.objects.get_or_create(name='Usuario')[0])
        self.client.force_login(self.admin)

    def test_lista_no_muestra_estudiantes(self):
        html=self.client.get(reverse('usuarios_lista')).content.decode()
        self.assertIn('bib_sp',html);self.assertIn('adm_sp',html);self.assertNotIn('estu_sp',html)
        self.assertNotIn('value="Usuario"',html)
        self.assertNotIn('estu_sp',self.client.get(reverse('usuarios_lista')+'?rol=Usuario').content.decode())

    def test_no_se_puede_editar_ni_eliminar_estudiante_aqui(self):
        self.assertEqual(self.client.get(reverse('usuarios_editar',args=[self.estudiante.pk])).status_code,404)
        self.assertEqual(self.client.post(reverse('usuarios_eliminar',args=[self.estudiante.pk])).status_code,404)
        self.assertTrue(User.objects.filter(pk=self.estudiante.pk).exists())

    def test_crear_solo_ofrece_bibliotecario_y_administrador(self):
        html=self.client.get(reverse('usuarios_nuevo')).content.decode()
        self.assertIn('value="Bibliotecario"',html);self.assertIn('value="Administrador"',html);self.assertNotIn('value="Usuario"',html)
        self.assertNotIn('Volver a Usuarios',html)
        datos={'username':'estu2','email':'e2@t.com','rol':'Usuario','password1':'ClaveLarga123!','password2':'ClaveLarga123!','activo':'on'}
        self.assertEqual(self.client.post(reverse('usuarios_nuevo'),datos).status_code,200)
        self.assertFalse(User.objects.filter(username='estu2').exists())
        datos['rol']='Bibliotecario'
        self.assertEqual(self.client.post(reverse('usuarios_nuevo'),datos).status_code,302)
        self.assertTrue(User.objects.get(username='estu2').groups.filter(name='Bibliotecario').exists())
