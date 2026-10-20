# Sistema de Registro de Eventos TecNM

Aplicación Django para inscripción de alumnos, búsqueda y control de asistencia.

## Requisitos

- Python 3.11 o posterior
- MySQL 8 o compatible
- Git

## Preparar el proyecto en Windows

1. Clona el repositorio o descarga el ZIP desde GitHub y descomprímelo.
2. Abre PowerShell en la carpeta del proyecto y crea un entorno virtual:

	```powershell
	py -m venv venv
	.\venv\Scripts\Activate.ps1
	```

3. Instala las dependencias:

	```powershell
	pip install -r requirements.txt
	```

4. Crea una base MySQL vacía para el proyecto. En MySQL puedes ejecutar:

	```sql
	CREATE DATABASE evento_bd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
	```

	Copia `.env.example` como `.env`, genera una clave local y completa las variables de MySQL:

	```powershell
	python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
	```

	Pega el resultado en `SECRET_KEY` dentro de `.env`. Completa el usuario y contraseña locales de MySQL. No compartas el `.env`.
5. Aplica las migraciones y prepara el catálogo de carreras y eventos:

	```powershell
	python manage.py migrate
	python poblar_datos.py
	```

	Este cargador es idempotente: prepara carreras y dos eventos, pero **no crea alumnos**.

6. Crea una cuenta para entrar al dashboard:

	```powershell
	python manage.py createsuperuser
	```

7. Inicia el servidor:

	```powershell
	python manage.py runserver
	```

	Inscripción pública: `http://127.0.0.1:8000/`  
	Dashboard administrativo: `http://127.0.0.1:8000/dashboard/`

## Base de datos y privacidad

GitHub contiene el código y las migraciones, no la base MySQL ni los registros locales. Cada integrante crea su propia base vacía y la inicializa con las instrucciones anteriores. No subas respaldos, CURP, correos, contraseñas ni el archivo `.env`.

## Actividades de revisión

El plan de pruebas y documentación para Joel e Iván está en `docs/actividades_companeros.pdf`.
