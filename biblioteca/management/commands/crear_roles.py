from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Crea los grupos Bibliotecario y Usuario sin borrar registros.'
    def handle(self, *args, **kwargs):
        for nombre in ('Bibliotecario','Usuario'):
            Group.objects.get_or_create(name=nombre)
            self.stdout.write(self.style.SUCCESS(f'Grupo {nombre}: preparado'))
        self.stdout.write('Administrador = superusuario de Django. Los usuarios nuevos no reciben privilegios automáticamente.')
