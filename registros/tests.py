from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .forms import RegistroPublicoForm
from .models import ConfiguracionSitio, Carrera, Evento, Registro, validar_curp


class CurpValidatorTests(SimpleTestCase):
	def test_accepts_valid_curp_case_insensitively(self):
		validar_curp('gode561231hd frrn00'.replace(' ', ''))

	def test_rejects_invalid_check_digit(self):
		with self.assertRaises(ValidationError):
			validar_curp('GODE561231HDFRRN09')


class RegistroPublicoFormTests(TestCase):
	def setUp(self):
		self.carrera = Carrera.objects.create(nombre='Informática')
		self.evento = Evento.objects.create(nombre='Examen', fecha=date(2026, 10, 20))
		self.form_data = {
			'numero_control': '20260001',
			'curp': 'GODE561231HDFRRN00',
			'nombre': 'Ana',
			'apellido_paterno': 'López',
			'apellido_materno': '',
			'correo_institucional': 'ana@example.edu',
			'lengua_hablada': 'Chinanteco',
			'discapacidad': 'ninguna',
			'discapacidad_otra': '',
			'comunidad': 'San Juan',
			'semestre': 12,
			'carrera': self.carrera.pk,
			'evento': self.evento.pk,
		}

	def test_accepts_curp_and_optional_student_details(self):
		form = RegistroPublicoForm(data=self.form_data)
		self.assertTrue(form.is_valid(), form.errors)
		registro = form.save()
		self.assertEqual(registro.curp, 'GODE561231HDFRRN00')
		self.assertEqual(registro.lengua_hablada, 'Chinanteco')
		self.assertEqual(registro.comunidad, 'San Juan')

	def test_public_form_renders_new_fields(self):
		response = self.client.get(reverse('registro_publico'))
		self.assertContains(response, 'CURP')
		self.assertContains(response, 'Lengua que habla')
		self.assertContains(response, 'Comunidad o localidad donde vive')

	def test_successful_registration_displays_event_whatsapp_link(self):
		link = 'https://chat.whatsapp.com/invite-code'
		ConfiguracionSitio.objects.create(enlace_whatsapp=link)
		otro_evento = Evento.objects.create(nombre='Segundo examen', fecha=date(2026, 11, 1))
		data = {**self.form_data, 'evento': otro_evento.pk}
		response = self.client.post(reverse('registro_publico'), data, follow=True)
		self.assertContains(response, 'Unirme al grupo de WhatsApp')
		self.assertContains(response, link)

	def test_invalid_registration_does_not_display_whatsapp_link(self):
		ConfiguracionSitio.objects.create(enlace_whatsapp='https://chat.whatsapp.com/invite-code')
		self.form_data['curp'] = 'INVALIDA'
		response = self.client.post(reverse('registro_publico'), self.form_data)
		self.assertNotContains(response, 'Unirme al grupo de WhatsApp')

	def test_other_disability_requires_description(self):
		self.form_data['discapacidad'] = 'otra'
		form = RegistroPublicoForm(data=self.form_data)
		self.assertFalse(form.is_valid())
		self.assertIn('discapacidad_otra', form.errors)

	def test_curp_must_be_unique_for_event(self):
		Registro.objects.create(
			numero_control='20260002', curp=self.form_data['curp'], nombre='Luis',
			apellido_paterno='Pérez', correo_institucional='luis@example.edu', semestre=1,
			carrera=self.carrera, evento=self.evento,
		)
		form = RegistroPublicoForm(data=self.form_data)
		self.assertFalse(form.is_valid())
		self.assertIn('curp', form.errors)

	def test_inactive_career_is_not_available_for_registration(self):
		self.carrera.activa = False
		self.carrera.save(update_fields=['activa'])
		form = RegistroPublicoForm()
		self.assertNotIn(self.carrera, form.fields['carrera'].queryset)


class CarreraCatalogTests(TestCase):
	def test_active_catalog_has_requested_careers(self):
		self.assertSetEqual(
			set(Carrera.objects.filter(activa=True).values_list('nombre', flat=True)),
			{
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
			},
		)

	def test_mechatronics_and_its_registrations_are_archived(self):
		mecatronica = Carrera.objects.filter(nombre='Ing. Mecatrónica').first()
		self.assertFalse(Carrera.objects.filter(nombre='Ing. Mecatrónica', activa=True).exists())
		if mecatronica:
			self.assertFalse(mecatronica.activa)
			self.assertFalse(mecatronica.registro_set.filter(activo=True).exists())


class AsistenciaTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='departamento', password='test-pass')
		self.client.force_login(self.user)
		self.carrera = Carrera.objects.create(nombre='Informática')
		self.evento = Evento.objects.create(nombre='Examen', fecha=date(2026, 10, 20))
		self.asistio = self.crear_registro('20260001', True)
		self.no_asistio = self.crear_registro('20260002', False)
		self.no_asistio.nombre = 'Lucía'
		self.no_asistio.apellido_paterno = 'Morales'
		self.no_asistio.curp = 'GODE561231HDFRRN00'
		self.no_asistio.save(update_fields=['nombre', 'apellido_paterno', 'curp'])
		self.pendiente = self.crear_registro('20260003', None)

	def crear_registro(self, numero_control, asistio):
		return Registro.objects.create(
			numero_control=numero_control,
			nombre='Alumno',
			apellido_paterno='Prueba',
			correo_institucional=f'{numero_control}@example.edu',
			semestre=1,
			carrera=self.carrera,
			evento=self.evento,
			asistio=asistio,
		)

	def test_attendance_filter_and_export_only_no_shows(self):
		response = self.client.get(reverse('exportar_inasistencias'), {'evento': self.evento.pk})
		content = response.content.decode('utf-8-sig')
		self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')
		self.assertIn(self.no_asistio.numero_control, content)
		self.assertNotIn(self.asistio.numero_control, content)
		self.assertNotIn(self.pendiente.numero_control, content)

	def test_export_all_includes_all_attendance_states(self):
		response = self.client.get(reverse('exportar_registros_csv'), {'tipo': 'todos'})
		content = response.content.decode('utf-8-sig')
		self.assertIn(self.asistio.numero_control, content)
		self.assertIn(self.no_asistio.numero_control, content)
		self.assertIn(self.pendiente.numero_control, content)
		self.assertIn('Asistió', content)
		self.assertIn('No asistió', content)
		self.assertIn('Pendiente', content)

	def test_export_attended_only_excludes_other_states(self):
		response = self.client.get(reverse('exportar_registros_csv'), {'tipo': 'asistieron'})
		content = response.content.decode('utf-8-sig')
		self.assertIn(self.asistio.numero_control, content)
		self.assertNotIn(self.no_asistio.numero_control, content)
		self.assertNotIn(self.pendiente.numero_control, content)

	def test_department_can_mark_attendance(self):
		response = self.client.post(
			reverse('actualizar_asistencia', args=[self.pendiente.pk]),
			{'asistio': 'si', 'next': '/dashboard/'},
		)
		self.pendiente.refresh_from_db()
		self.assertTrue(self.pendiente.asistio)
		self.assertRedirects(response, '/dashboard/')

	def test_dashboard_renders_attendance_controls(self):
		response = self.client.get(reverse('dashboard'))
		self.assertContains(response, 'Asistencia')
		self.assertContains(response, 'Solo no asistieron')
		self.assertContains(response, 'Exportar hoja de cálculo')
		self.assertContains(response, 'Solo asistieron')
		self.assertContains(response, 'Configurar WhatsApp')

	def test_admin_can_configure_shared_whatsapp_link(self):
		link = 'https://chat.whatsapp.com/nuevo-grupo'
		self.client.post(reverse('configurar_whatsapp'), {
			'enlace_whatsapp': link,
		})
		configuracion = ConfiguracionSitio.objects.get(pk=1)
		self.assertEqual(configuracion.enlace_whatsapp, link)

	def test_dashboard_searches_by_control_name_and_curp(self):
		for term in ('20260002', 'Lucía Morales', 'GODE561231HDFRRN00'):
			with self.subTest(term=term):
				response = self.client.get(reverse('dashboard'), {'q': term})
				self.assertContains(response, self.no_asistio.numero_control)
				self.assertNotContains(response, self.asistio.numero_control)

	def test_no_show_export_respects_search(self):
		response = self.client.get(reverse('exportar_inasistencias'), {'q': 'Lucía Morales'})
		content = response.content.decode('utf-8-sig')
		self.assertIn(self.no_asistio.numero_control, content)
		self.assertNotIn(self.pendiente.numero_control, content)
