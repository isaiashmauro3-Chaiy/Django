from django import forms
from .models import Registro, Evento

class RegistroPublicoForm(forms.ModelForm):
    class Meta:
        model = Registro
        fields = ['numero_control', 'curp', 'nombre', 'apellido_paterno', 'apellido_materno', 'correo_institucional', 'lengua_hablada', 'discapacidad', 'discapacidad_otra', 'comunidad', 'semestre', 'carrera', 'evento']
        widgets = {
            'numero_control': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 19350244', 'required': 'required'}),
            'curp': forms.TextInput(attrs={'class': 'field-input', 'placeholder': '18 caracteres', 'maxlength': '18', 'autocomplete': 'off', 'autocapitalize': 'characters'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Juan Pablo', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Gómez', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Pérez (Opcional)'}),
            'correo_institucional': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@tuxtepec.tecnm.mx', 'required': 'required'}),
            'lengua_hablada': forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Ej. Español, Chinanteco'}),
            'discapacidad': forms.Select(attrs={'class': 'field-select'}),
            'discapacidad_otra': forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Escribe cuál'}),
            'comunidad': forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Nombre de la comunidad o localidad'}),
            'semestre': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'carrera': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'evento': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curp'].required = True
        # Restricción: El alumno solo puede inscribirse en eventos activos
        self.fields['evento'].queryset = Evento.objects.filter(activo=True)
        self.fields['carrera'].queryset = self.fields['carrera'].queryset.filter(activa=True).order_by('nombre')

    def clean_curp(self):
        return self.cleaned_data['curp'].strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        discapacidad = cleaned_data.get('discapacidad')
        discapacidad_otra = cleaned_data.get('discapacidad_otra', '').strip()

        if discapacidad == 'otra' and not discapacidad_otra:
            self.add_error('discapacidad_otra', 'Escribe cuál es la discapacidad.')
        elif discapacidad != 'otra':
            cleaned_data['discapacidad_otra'] = ''

        curp = cleaned_data.get('curp')
        evento = cleaned_data.get('evento')
        if curp and evento and Registro.objects.filter(curp=curp, evento=evento).exclude(pk=self.instance.pk).exists():
            self.add_error('curp', 'Ya existe un registro con esta CURP para el evento seleccionado.')

        return cleaned_data
