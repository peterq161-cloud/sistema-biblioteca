from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Los estudiantes (rol Usuario) se gestionan en «Cuentas de usuarios».
ROLES = [('Bibliotecario','Bibliotecario'),('Administrador','Administrador')]

class UsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=ROLES, initial='Bibliotecario', label='Rol')
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
        if self.es_creacion:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
        else:
            u=self.instance
            self.fields['rol'].initial = 'Administrador' if u.is_superuser else 'Bibliotecario'
            self.fields['activo'].initial = u.is_active
        for field in self.fields.values():
            field.widget.attrs['class']='campo'
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
        return data
