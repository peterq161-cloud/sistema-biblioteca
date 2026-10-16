from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Lector

class CuentaForm(forms.ModelForm):
    lector = forms.ModelChoiceField(queryset=Lector.objects.none(), required=False, label='Lector vinculado')
    activo = forms.BooleanField(required=False, initial=True, label='Cuenta activa')
    password1 = forms.CharField(required=False, widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(required=False, widget=forms.PasswordInput, label='Confirmar contraseña')
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        labels = {'first_name':'Nombre', 'last_name':'Apellido', 'username':'Nombre de usuario', 'email':'Correo electrónico'}
    def __init__(self,*args,**kwargs):
        self.creando = kwargs.get('instance') is None
        super().__init__(*args,**kwargs)
        self.fields['lector'].queryset = Lector.objects.order_by('nombre_completo')
        self.fields['lector'].label_from_instance = lambda l: f'{l.nombre_completo} ({l.carnet})'
        if not self.creando:
            self.fields.pop('username')
            self.fields.pop('password1')
            self.fields.pop('password2')
            self.fields['activo'].initial = self.instance.is_active
            lectores = Lector.objects.filter(correo__iexact=self.instance.email) if self.instance.email else Lector.objects.none()
            if lectores.count()==1:self.fields['lector'].initial=lectores.first()
        else:
            self.fields['password1'].required=True
            self.fields['password2'].required=True
        for f in self.fields.values():f.widget.attrs['class']='campo'
    def clean_email(self):
        email=self.cleaned_data.get('email','').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya pertenece a otra cuenta.')
        return email
    def clean(self):
        data=super().clean()
        lector=data.get('lector');email=data.get('email','')
        if lector:
            if not lector.correo:self.add_error('lector','El lector necesita un correo electrónico.')
            elif email and lector.correo.casefold()!=email.casefold():self.add_error('email','El correo debe coincidir con el del lector.')
            elif not email:data['email']=lector.correo.lower()
        elif email:
            if Lector.objects.filter(correo__iexact=email).count()!=1:self.add_error('lector','No existe un lector único con ese correo. Selecciona uno válido.')
        else:self.add_error('lector','Selecciona un lector con correo electrónico.')
        if self.creando:
            p1=data.get('password1');p2=data.get('password2')
            if p1!=p2:self.add_error('password2','Las contraseñas no coinciden.')
            elif p1:
                try:validate_password(p1,self.instance)
                except ValidationError as e:self.add_error('password1',e)
        return data

class CuentaPasswordForm(forms.Form):
    password1=forms.CharField(label='Nueva contraseña',widget=forms.PasswordInput(attrs={'class':'campo'}))
    password2=forms.CharField(label='Confirmar contraseña',widget=forms.PasswordInput(attrs={'class':'campo'}))
    def __init__(self,*args,usuario=None,**kwargs):
        super().__init__(*args,**kwargs);self.usuario=usuario
    def clean(self):
        data=super().clean();p1=data.get('password1');p2=data.get('password2')
        if p1!=p2:self.add_error('password2','Las contraseñas no coinciden.')
        elif p1:
            try:validate_password(p1,self.usuario)
            except ValidationError as e:self.add_error('password1',e)
        return data
