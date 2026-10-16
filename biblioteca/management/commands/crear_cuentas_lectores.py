import re
import unicodedata

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from biblioteca.models import Lector


def _usuario_base(correo):
    base = unicodedata.normalize('NFKD', correo.split('@')[0]).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9._-]', '', base.lower()) or 'lector'


class Command(BaseCommand):
    help = ('Crea una cuenta de rol Usuario para cada lector que tenga correo y todavía no tenga cuenta. '
            'La cuenta se vincula con el lector por el correo. No cambia ni borra cuentas existentes.')

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Contraseña inicial igual para todas las cuentas nuevas.')

    @transaction.atomic
    def handle(self, *args, **opts):
        password = opts['password']
        if len(password) < 8:
            raise CommandError('La contraseña debe tener al menos 8 caracteres.')
        grupo, _ = Group.objects.get_or_create(name='Usuario')
        creadas = omitidas = 0
        for lector in Lector.objects.exclude(correo='').order_by('carnet'):
            correo = lector.correo.strip().lower()
            if User.objects.filter(email__iexact=correo).exists():
                self.stdout.write(f'Omitido {lector.carnet}: ya existe una cuenta con {correo}')
                omitidas += 1
                continue
            base = _usuario_base(correo)
            username, n = base, 2
            while User.objects.filter(username__iexact=username).exists():
                username, n = f'{base}{n}', n + 1
            partes = lector.nombre_completo.split()
            user = User(username=username, email=correo, first_name=(partes[0] if partes else '')[:150],
                        last_name=' '.join(partes[1:])[:150], is_active=True, is_staff=False, is_superuser=False)
            user.set_password(password)
            user.save()
            user.groups.add(grupo)
            creadas += 1
            self.stdout.write(self.style.SUCCESS(f'Creada {lector.carnet}: usuario {username}'))
        self.stdout.write(f'Listo: {creadas} cuentas creadas, {omitidas} omitidas.')
