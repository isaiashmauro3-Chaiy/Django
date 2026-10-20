from datetime import date
import re

from django.core.exceptions import ValidationError
from django.db import models


def validar_curp(value):
    curp = value.upper()
    pattern = r'^[A-Z][AEIOUX][A-Z]{2}\d{6}[HMX][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$'
    if not re.fullmatch(pattern, curp):
        raise ValidationError('Ingresa una CURP de 18 caracteres con formato válido.')

    estados = {
        'AS', 'BC', 'BS', 'CC', 'CL', 'CM', 'CS', 'CH', 'DF', 'DG', 'GT',
        'GR', 'HG', 'JC', 'MC', 'MN', 'MS', 'NT', 'NL', 'OC', 'PL', 'QT',
        'QR', 'SP', 'SL', 'SR', 'TC', 'TS', 'TL', 'VZ', 'YN', 'ZS', 'NE',
    }
    if curp[11:13] not in estados:
        raise ValidationError('La clave de estado de la CURP no es válida.')

    try:
        date(2000, int(curp[6:8]), int(curp[8:10]))
    except ValueError:
        raise ValidationError('La fecha de nacimiento de la CURP no es válida.')

    caracteres = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ'
    valores = {character: index for index, character in enumerate(caracteres)}
    suma = sum(valores[character] * (18 - index) for index, character in enumerate(curp[:17]))
    digito_verificador = (10 - suma % 10) % 10
    if int(curp[17]) != digito_verificador:
        raise ValidationError('El dígito verificador de la CURP no es válido.')

class Carrera(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre de la Carrera")
    activa = models.BooleanField(default=True, verbose_name="Carrera Activa")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"


class Evento(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Evento")
    fecha = models.DateField(verbose_name="Fecha del Evento")
    cupo_maximo = models.PositiveIntegerField(null=True, blank=True, verbose_name="Cupo Máximo (opcional)")
    activo = models.BooleanField(default=True, verbose_name="Evento Activo")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"


class ConfiguracionSitio(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enlace_whatsapp = models.URLField(blank=True, default="", verbose_name="Enlace de WhatsApp")

    class Meta:
        verbose_name = "Configuración del sitio"
        verbose_name_plural = "Configuración del sitio"

    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Enlace de WhatsApp compartido"


class Registro(models.Model):
    SEMESTRES_CHOICES = [
        (1, '1er Semestre'),
        (2, '2do Semestre'),
        (3, '3er Semestre'),
        (4, '4to Semestre'),
        (5, '5to Semestre'),
        (6, '6to Semestre'),
        (7, '7mo Semestre'),
        (8, '8vo Semestre'),
        (9, '9no Semestre'),
        (10, '10mo Semestre'),
        (11, '11vo Semestre'),
        (12, '12vo Semestre'),
    ]

    DISCAPACIDAD_CHOICES = [
        ('', 'Selecciona una opción'),
        ('ninguna', 'No presenta discapacidad'),
        ('visual', 'Visual'),
        ('auditiva', 'Auditiva'),
        ('motriz', 'Motriz o física'),
        ('intelectual', 'Intelectual'),
        ('psicosocial', 'Psicosocial'),
        ('multiple', 'Múltiple'),
        ('otra', 'Otra'),
        ('prefiero_no_responder', 'Prefiero no responder'),
    ]

    numero_control = models.CharField(max_length=15, verbose_name="Número de Control")
    curp = models.CharField(max_length=18, null=True, blank=True, validators=[validar_curp], verbose_name="CURP")
    nombre = models.CharField(max_length=100, verbose_name="Nombre(s)", default="")
    apellido_paterno = models.CharField(max_length=100, verbose_name="Apellido Paterno", default="")
    apellido_materno = models.CharField(max_length=100, verbose_name="Apellido Materno", blank=True, default="")
    correo_institucional = models.EmailField(max_length=150, verbose_name="Correo Institucional", default="")
    lengua_hablada = models.CharField(max_length=100, blank=True, default="", verbose_name="Lengua que habla")
    discapacidad = models.CharField(max_length=30, choices=DISCAPACIDAD_CHOICES, blank=True, default="", verbose_name="Discapacidad")
    discapacidad_otra = models.CharField(max_length=150, blank=True, default="", verbose_name="Otra discapacidad")
    comunidad = models.CharField(max_length=150, blank=True, default="", verbose_name="Comunidad de residencia")
    semestre = models.PositiveSmallIntegerField(choices=SEMESTRES_CHOICES, verbose_name="Semestre")
    carrera = models.ForeignKey(Carrera, on_delete=models.RESTRICT, verbose_name="Carrera")
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, verbose_name="Evento a Inscribir")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    activo = models.BooleanField(default=True, verbose_name="Registro Activo")
    asistio = models.BooleanField(null=True, blank=True, default=None, verbose_name="Asistió al examen")

    class Meta:
        verbose_name = "Registro de Alumno"
        verbose_name_plural = "Registros de Alumnos"
        # Un alumno no puede inscribirse al mismo evento dos veces
        constraints = [
            models.UniqueConstraint(fields=['numero_control', 'evento'], name='unique_registro_evento'),
            models.UniqueConstraint(fields=['curp', 'evento'], name='unique_curp_evento'),
        ]

    @property
    def nombre_completo(self):
        parts = [self.nombre, self.apellido_paterno, self.apellido_materno]
        return " ".join([p for p in parts if p]).strip()

    @property
    def asistencia_estado(self):
        if self.asistio is None:
            return 'Pendiente'
        return 'Asistió' if self.asistio else 'No asistió'

    def __str__(self):
        return f"{self.numero_control} - {self.nombre_completo} ({self.evento.nombre})"
