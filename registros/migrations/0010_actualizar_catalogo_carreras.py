from django.db import migrations


CARRERAS_ACTIVAS = [
    'Lic. Administración',
    'Lic. Contador Público',
    'Ing. Gestión Empresarial',
    'Ing. Bioquímica',
    'Ing. Electromecánica',
    'Ing. Electrónica',
    'Ing. Sistemas Computacionales',
    'Ing. Informática',
    'Ing. Desarrollo de Aplicaciones',
    'Ing. Civil',
    'Lic. Arquitectura',
]


def actualizar_catalogo(apps, schema_editor):
    Carrera = apps.get_model('registros', 'Carrera')
    Registro = apps.get_model('registros', 'Registro')
    db_alias = schema_editor.connection.alias

    Carrera.objects.using(db_alias).filter(nombre='Ing. Informatica').update(nombre='Ing. Informática')

    for nombre in CARRERAS_ACTIVAS:
        Carrera.objects.using(db_alias).get_or_create(nombre=nombre, defaults={'activa': True})
        Carrera.objects.using(db_alias).filter(nombre=nombre).update(activa=True)

    carrera_mecatronica = Carrera.objects.using(db_alias).filter(nombre='Ing. Mecatrónica').first()
    if carrera_mecatronica:
        Registro.objects.using(db_alias).filter(
            carrera_id=carrera_mecatronica.pk,
            activo=True,
        ).update(activo=False)
        carrera_mecatronica.activa = False
        carrera_mecatronica.save(update_fields=['activa'], using=db_alias)


def revertir_catalogo(apps, schema_editor):
    Carrera = apps.get_model('registros', 'Carrera')
    Carrera.objects.using(schema_editor.connection.alias).filter(
        nombre__in=CARRERAS_ACTIVAS,
    ).exclude(nombre='Lic. Administración').exclude(nombre='Ing. Gestión Empresarial').exclude(
        nombre='Ing. Bioquímica',
    ).exclude(nombre='Ing. Electromecánica').exclude(nombre='Ing. Sistemas Computacionales').exclude(
        nombre='Ing. Informática',
    ).update(activa=False)


class Migration(migrations.Migration):
    dependencies = [
        ('registros', '0009_carrera_activa'),
    ]

    operations = [
        migrations.RunPython(actualizar_catalogo, revertir_catalogo),
    ]
