import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evento_matematico.settings')
django.setup()

from registros.models import Carrera, Evento


CARRERAS = [
    "Ing. Informática",
    "Ing. Bioquímica",
    "Ing. Civil",
    "Ing. Desarrollo de Aplicaciones",
    "Ing. Electromecánica",
    "Ing. Electrónica",
    "Ing. Gestión Empresarial",
    "Ing. Sistemas Computacionales",
    "Lic. Contador Público",
    "Lic. Arquitectura",
    "Lic. Administración",
]

EVENTOS = [
    ("Ciencias Básicas", date(2026, 11, 2)),
    ("Ciencias Económica-Administrativa", date(2026, 11, 3)),
]

ALIAS_EVENTOS = {
    "Ciencias Básicas": ["Ciencias Básicas", "Ciencias Basicas", "Examen de Ciencias Básicas"],
    "Ciencias Económica-Administrativa": [
        "Ciencias Económica-Administrativa",
        "Ciencias Económico-Administrativa",
        "Examen de Ciencias Económico-Administrativas",
    ],
}

for nombre in CARRERAS:
    Carrera.objects.get_or_create(nombre=nombre, defaults={"activa": True})

for nombre, fecha in EVENTOS:
    evento = Evento.objects.filter(nombre__in=ALIAS_EVENTOS[nombre]).order_by("id").first()
    if evento is None:
        Evento.objects.create(nombre=nombre, fecha=fecha, activo=True)
    elif evento.nombre != nombre:
        evento.nombre = nombre
        evento.save(update_fields=["nombre"])

print("Catálogo preparado: carreras y eventos cargados; no se crearon alumnos.")
