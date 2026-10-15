from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Lector

ROLES = [('Usuario','Usuario'),('Bibliotecario','Bibliotecario'),('Administrador','Administrador')]

class UsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=ROLES, initial='Usuario', label='Rol')
    lector = forms.ModelChoiceField(queryset=Lector.objects.none(), required=False, label='Lector vinculado', empty_label='Selecciona un lector (opcional)')
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput, required=False)
    activo = forms.BooleanField(label='Cuenta activa', required=False, initial=True)

    class Meta:
        model = User
        fields = ['first_name','last_name','username','email']
        labels = {'first_name':'Nombre','last_name':'Apellido','username':'Nombre de usuario','email':'Correo electrónico'}

    def __init__(self, *args, **kwargs):
        self.es_creacion = kwargs.get('instance') is None
        super().__init__(*args, **kwargs)
        self.fields['lector'].queryset = Lector.objects.order_by('nombre_completo')
        if self.es_creacion:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
        else:
            u=self.instance
            self.fields['rol'].initial = 'Administrador' if u.is_superuser else ('Bibliotecario' if u.groups.filter(name='Bibliotecario').exists() else 'Usuario')
            self.fields['activo'].initial = u.is_active
            if u.email:
                matches=Lector.objects.filter(correo__iexact=u.email)
                if matches.count()==1:self.fields['lector'].initial=matches.first()
        for field in self.fields.values():
            field.widget.attrs['class']='campo'
        self.fields['lector'].help_text='Escribe en el buscador para localizar al lector. El vínculo utiliza su correo electrónico.'
        self.fields['password1'].help_text='Al editar, deja vacío para conservar la contraseña.'

    def clean_email(self):
        email=self.cleaned_data['email'].strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya está registrado por otro usuario.')
        return email

    def clean(self):
        data=super().clean()
        p1=data.get('password1');p2=data.get('password2')
        if p1 or p2:
            if p1!=p2:self.add_error('password2','Las contraseñas no coinciden.')
            elif p1:
                try:validate_password(p1,self.instance)
                except ValidationError as exc:self.add_error('password1',exc)
        if data.get('rol')=='Usuario':
            lector=data.get('lector')
            if lector:
                if not lector.correo:self.add_error('lector','El lector seleccionado necesita un correo electrónico para vincularse.')
                elif data.get('email') and data['email'].casefold()!=lector.correo.casefold():
                    self.add_error('email','El correo debe coincidir con el del lector seleccionado.')
                elif not data.get('email'):data['email']=lector.correo.lower()
            elif data.get('email'):
                encontrados=Lector.objects.filter(correo__iexact=data['email'])
                if encontrados.count()!=1:self.add_error('lector','No hay un lector único con ese correo. Regístralo o selecciónalo.')
            else:self.add_error('lector','Selecciona un lector con correo electrónico.')
        return data
