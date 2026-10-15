import re
from datetime import timedelta

from django import forms
from datetime import date

from .models import Libro, Lector, Prestamo

MAX_PRESTAMOS_POR_LECTOR = 3
DIAS_PRESTAMO = 14


class EstiloMixin:
    """Añade la clase CSS 'campo' a todos los widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'campo')


class LibroForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Libro
        fields = ['titulo', 'autor', 'categoria', 'editorial',
                  'anio_publicacion', 'isbn', 'cantidad_total']
        labels = {
            'titulo': 'Título',
            'autor': 'Autor',
            'categoria': 'Categoría',
            'editorial': 'Editorial',
            'anio_publicacion': 'Año de publicación',
            'isbn': 'ISBN',
            'cantidad_total': 'Ejemplares en total',
        }
        help_texts = {
            'isbn': 'Diez o trece dígitos. Los guiones se ignoran.',
            'cantidad_total': 'Los ejemplares disponibles se calculan solos al prestar y devolver.',
        }
        error_messages = {
            'isbn': {'unique': 'Ya existe un libro registrado con ese ISBN.'},
        }
        widgets = {
            'cantidad_total': forms.NumberInput(attrs={'min': 1}),
            'anio_publicacion': forms.NumberInput(attrs={'min': 1000}),
        }

    def clean_titulo(self):
        return ' '.join(self.cleaned_data['titulo'].split())

    def clean_autor(self):
        return ' '.join(self.cleaned_data['autor'].split())

    def clean_isbn(self):
        isbn = re.sub(r'[\s-]', '', self.cleaned_data['isbn']).upper()
        if not re.fullmatch(r'\d{9}[\dX]|\d{13}', isbn):
            raise forms.ValidationError(
                'El ISBN debe tener 10 o 13 dígitos (por ejemplo 9780307474728).')
        return isbn

    def clean_anio_publicacion(self):
        anio = self.cleaned_data.get('anio_publicacion')
        if anio is not None and not (1000 <= anio <= date.today().year):
            raise forms.ValidationError(
                f'Escribe un año entre 1000 y {date.today().year}.')
        return anio

    def clean_cantidad_total(self):
        total = self.cleaned_data['cantidad_total']
        if total < 1:
            raise forms.ValidationError('Debe haber al menos un ejemplar.')
        if self.instance.pk:
            prestados = self.instance.prestamo_set.filter(estado='Activo').count()
            if total < prestados:
                raise forms.ValidationError(
                    f'Hay {prestados} ejemplares prestados; el total no puede ser menor.')
        return total

    def save(self, commit=True):
        libro = super().save(commit=False)
        prestados = 0
        if libro.pk:
            prestados = libro.prestamo_set.filter(estado='Activo').count()
        libro.cantidad_disponible = libro.cantidad_total - prestados
        libro.estado = 'Disponible' if libro.cantidad_disponible > 0 else 'Agotado'
        if commit:
            libro.save()
        return libro


class LectorForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Lector
        fields = ['nombre_completo', 'correo', 'telefono']
        labels = {'nombre_completo': 'Nombre completo', 'correo': 'Correo electrónico', 'telefono': 'Teléfono'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        carnet = self.instance.carnet if self.instance.pk else self.siguiente_carnet()
        self.fields['carnet_mostrado'] = forms.CharField(label='Carnet (automático)', initial=carnet, required=False,
            widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'campo', 'aria-label': 'Carnet automático'}))
        # El campo informativo no se usa para guardar: nunca confiar en el cliente.
        self.order_fields(['nombre_completo', 'carnet_mostrado', 'correo', 'telefono'])

    @staticmethod
    def siguiente_carnet():
        maximo = 0
        for carnet in Lector.objects.filter(carnet__startswith='LC-').values_list('carnet', flat=True):
            if carnet[3:].isdigit():
                maximo = max(maximo, int(carnet[3:]))
        return f'LC-{maximo + 1:04d}'

    def clean_nombre_completo(self):
        nombre = ' '.join(self.cleaned_data['nombre_completo'].split())
        if len(nombre) < 3:
            raise forms.ValidationError('Escribe el nombre completo del lector.')
        return nombre

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono and not re.fullmatch(r'[0-9+\-\s()]{7,20}', telefono):
            raise forms.ValidationError('Escribe un teléfono válido, por ejemplo 809-555-0101.')
        return telefono


class PrestamoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['libro', 'lector', 'fecha_devolucion']
        labels = {
            'libro': 'Libro',
            'lector': 'Lector',
            'fecha_devolucion': 'Fecha límite de devolución',
        }
        widgets = {
            'fecha_devolucion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['libro'].queryset = (
            Libro.objects.all().order_by('titulo'))
        self.fields['libro'].label_from_instance = (
            lambda l: f'{l.titulo} — {l.autor} ({l.cantidad_disponible} disp.)')
        self.fields['libro'].empty_label = 'Elige un libro'
        self.fields['libro'].widget = forms.HiddenInput(attrs={'data-autocomplete-id': 'libro'})
        self.fields['lector'].queryset = Lector.objects.order_by('nombre_completo')
        self.fields['lector'].label_from_instance = (
            lambda l: f'{l.nombre_completo} ({l.carnet})')
        self.fields['lector'].empty_label = 'Elige un lector'
        self.fields['lector'].widget = forms.HiddenInput(attrs={'data-autocomplete-id': 'lector'})
        self.fields['fecha_devolucion'].required = True
        self.fields['fecha_devolucion'].initial = (
            date.today() + timedelta(days=DIAS_PRESTAMO))

    def clean_fecha_devolucion(self):
        fecha = self.cleaned_data['fecha_devolucion']
        if fecha < date.today():
            raise forms.ValidationError('La fecha límite no puede estar en el pasado.')
        return fecha

    def clean(self):
        datos = super().clean()
        libro = datos.get('libro')
        lector = datos.get('lector')
        if libro and lector:
            activos = Prestamo.objects.filter(lector=lector, estado='Activo')
            if activos.filter(fecha_devolucion__lt=date.today()).exists():
                self.add_error('lector', 'Este lector tiene un préstamo vencido. Debe devolverlo antes de solicitar otro.')
            elif activos.filter(libro=libro).exists():
                self.add_error('lector', 'Este lector ya tiene prestado este libro.')
            elif activos.count() >= MAX_PRESTAMOS_POR_LECTOR:
                self.add_error(
                    'lector',
                    f'Este lector ya tiene {MAX_PRESTAMOS_POR_LECTOR} préstamos activos, '
                    'que es el máximo permitido.')
        return datos


class PrestamoEditForm(EstiloMixin, forms.ModelForm):
    """Un préstamo activo solo permite ajustar la fecha límite."""

    class Meta:
        model = Prestamo
        fields = ['fecha_devolucion']
        labels = {'fecha_devolucion': 'Fecha límite de devolución'}
        widgets = {
            'fecha_devolucion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_devolucion'].required = True

    def clean_fecha_devolucion(self):
        fecha = self.cleaned_data['fecha_devolucion']
        if fecha < date.today():
            raise forms.ValidationError('La fecha límite no puede estar en el pasado.')
        return fecha
