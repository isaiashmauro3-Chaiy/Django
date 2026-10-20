from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models import CharField, Count, Q, Value
from django.core.paginator import Paginator
from django.db.models.functions import Concat
from django.utils.http import url_has_allowed_host_and_scheme
import csv
from .forms import RegistroPublicoForm
from .models import ConfiguracionSitio, Registro, Carrera, Evento

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

CARRERA_COLOR_MAP = {
    'Ing. Informática': '#047857',              # Verde TecNM
    'Ing. Bioquímica': '#0284c7',               # Azul Cielo
    'Ing. Electromecánica': '#f59e0b',          # Ámbar / Naranja
    'Ing. Gestión Empresarial': '#10b981',      # Verde Esmeralda
    'Ing. Mecatrónica': '#6366f1',              # Índigo / Violeta
    'Lic. Administración': '#ec4899',           # Rosa / Magenta
    'Ing. Sistemas Computacionales': '#8b5cf6', # Púrpura
    'Ing. Desarrollo de Aplicaciones': '#06b6d4', # Cian
    'Lic. Contador Público': '#f97316',
    'Ing. Electrónica': '#0ea5e9',
    'Ing. Civil': '#84cc16',
    'Lic. Arquitectura': '#d946ef',
}


def filtrar_por_busqueda(registros, termino):
    if not termino:
        return registros

    return registros.annotate(
        nombre_busqueda=Concat(
            'nombre', Value(' '), 'apellido_paterno', Value(' '), 'apellido_materno',
            output_field=CharField(),
        )
    ).filter(
        Q(numero_control__icontains=termino)
        | Q(curp__icontains=termino)
        | Q(nombre_busqueda__icontains=termino)
    )

def generar_grafica_pastel(labels, values, titulo, custom_colors=None):
    if not labels or not values or sum(values) == 0:
        return None
    try:
        fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=100)
        default_palette = ['#047857', '#0284c7', '#f59e0b', '#10b981', '#6366f1', '#ec4899', '#8b5cf6', '#64748b']
        colors = custom_colors if custom_colors else default_palette[:len(values)]
        
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=140,
            colors=colors,
            textprops=dict(color="#1e293b", weight="bold")
        )
        for text in texts:
            text.set_fontsize(8)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
        ax.set_title(titulo, fontsize=10, fontweight='bold', color='#047857', pad=10)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        return None

def registro_publico(request):
    """
    VISTA PÚBLICA:
    Cualquier alumno accede a esta ruta. Procesa y guarda el registro.
    """
    if request.method == 'POST':
        form = RegistroPublicoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                configuracion = ConfiguracionSitio.objects.filter(pk=1).first()
                request.session['enlace_whatsapp_registro'] = configuracion.enlace_whatsapp if configuracion else ''
                messages.success(request, "¡Tu registro se ha completado con éxito! Recuerda que no puedes modificarlo, en caso de error acude a administración.")
                return redirect('registro_publico') 
            except Exception as e:
                messages.error(request, "No se pudo completar el registro. Comprueba que no estés inscrito previamente en ese evento.")
        else:
            messages.error(request, "Por favor revisa el formulario, existen campos inválidos.")
    else:
        form = RegistroPublicoForm()

    enlace_whatsapp = request.session.pop('enlace_whatsapp_registro', '')
    return render(request, 'registros/registro_publico.html', {
        'form': form,
        'enlace_whatsapp_exito': enlace_whatsapp,
    })

@login_required
def dashboard_admin(request):
    """
    DASHBOARD ADMINISTRATIVO:
    Métricas para Chart.js y tabla de registros con filtros avanzados.
    """
    evento_id = request.GET.get('evento')
    carrera_ids = [c for c in request.GET.getlist('carrera') if c]
    semestres = [s for s in request.GET.getlist('semestre') if s]
    asistencia = request.GET.get('asistencia', '')
    busqueda = request.GET.get('q', '').strip()
    orden = request.GET.get('orden', 'recientes')
    
    registros = Registro.objects.select_related('carrera', 'evento').filter(activo=True)
    registros = filtrar_por_busqueda(registros, busqueda)
    registros_papelera = Registro.objects.select_related('carrera', 'evento').filter(activo=False).order_by('-fecha_registro')
    
    # Aplicar Filtros (Soporte Múltiple)
    if evento_id:
        registros = registros.filter(evento_id=evento_id)
    if carrera_ids:
        registros = registros.filter(carrera_id__in=carrera_ids)
    if semestres:
        registros = registros.filter(semestre__in=semestres)
    if asistencia == 'si':
        registros = registros.filter(asistio=True)
    elif asistencia == 'no':
        registros = registros.filter(asistio=False)
    elif asistencia == 'pendiente':
        registros = registros.filter(asistio__isnull=True)
        
    # Gráficas (agrupamiento limpio sin order_by del modelo)
    carreras_data = registros.order_by().values('carrera__nombre').annotate(total=Count('id')).order_by('-total')
    labels_carrera = [c['carrera__nombre'] for c in carreras_data]
    data_carrera = [c['total'] for c in carreras_data]
    colores_carrera = [CARRERA_COLOR_MAP.get(name, '#64748b') for name in labels_carrera]
    
    semestres_data = registros.order_by().values('semestre').annotate(total=Count('id')).order_by('semestre')
    labels_semestre = [f"{s['semestre']}° Semestre" for s in semestres_data]
    data_semestre = [s['total'] for s in semestres_data]
    
    # Aplicar Ordenamiento a la tabla
    if orden == 'az':
        registros = registros.order_by('apellido_paterno', 'apellido_materno', 'nombre')
    elif orden == 'za':
        registros = registros.order_by('-apellido_paterno', '-apellido_materno', '-nombre')
    elif orden == 'antiguos':
        registros = registros.order_by('fecha_registro')
    else:
        registros = registros.order_by('-fecha_registro')
        
    total_inscripciones = registros.count()
    
    # Paginación (20 por página)
    paginator = Paginator(registros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filtros = request.GET.copy()
    filtros.pop('page', None)
    filtros_query_string = filtros.urlencode()
    
    eventos = Evento.objects.all()
    carreras_lista = Carrera.objects.filter(activa=True).order_by('nombre')
    
    # Construir query string para el botón PDF
    query_params = []
    if evento_id:
        query_params.append(f"evento={evento_id}")
    for c in carrera_ids:
        query_params.append(f"carrera={c}")
    for s in semestres:
        query_params.append(f"semestre={s}")
    query_params.append(f"orden={orden}")
    pdf_query_string = "&".join(query_params)
    
    context = {
        'total_inscripciones': total_inscripciones,
        'registros': page_obj, 
        'labels_carrera': labels_carrera,
        'data_carrera': data_carrera,
        'colores_carrera': colores_carrera,
        'labels_semestre': labels_semestre,
        'data_semestre': data_semestre,
        'eventos': eventos,
        'carreras_lista': carreras_lista,
        'semestres_choices': Registro.SEMESTRES_CHOICES,
        'registros_papelera': registros_papelera,
        # Filtros seleccionados (Arrays para multi-select)
        'evento_seleccionado': int(evento_id) if evento_id else '',
        'carreras_seleccionadas': [int(c) for c in carrera_ids if c.isdigit()],
        'semestres_seleccionados': [int(s) for s in semestres if s.isdigit()],
        'asistencia_seleccionada': asistencia,
        'busqueda': busqueda,
        'asistencia_choices': [('pendiente', 'Pendiente'), ('si', 'Asistió'), ('no', 'No asistió')],
        'filtros_query_string': filtros_query_string,
        'orden_seleccionado': orden,
        'pdf_query_string': pdf_query_string,
        'configuracion_whatsapp': ConfiguracionSitio.objects.filter(pk=1).first(),
    }
    return render(request, 'registros/dashboard.html', context)


@login_required
def actualizar_asistencia(request, registro_id):
    if request.method != 'POST':
        return redirect('dashboard')

    registro = get_object_or_404(Registro, pk=registro_id, activo=True)
    estados = {'pendiente': None, 'si': True, 'no': False}
    estado = request.POST.get('asistio')
    if estado not in estados:
        messages.error(request, 'Selecciona un estado de asistencia válido.')
    else:
        registro.asistio = estados[estado]
        registro.save(update_fields=['asistio'])
        messages.success(request, f'Asistencia actualizada para {registro.nombre_completo}.')

    destino = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect('dashboard')


@login_required
def configurar_whatsapp(request):
    if request.method == 'POST':
        configuracion = ConfiguracionSitio.get_solo()
        configuracion.enlace_whatsapp = request.POST.get('enlace_whatsapp', '').strip()
        try:
            configuracion.full_clean()
            configuracion.save()
            messages.success(request, 'El enlace compartido de WhatsApp se actualizó correctamente.')
        except ValidationError as error:
            messages.error(request, f"No se pudo guardar el enlace: {' '.join(error.messages)}")
    return redirect('dashboard')


@login_required
def exportar_registros_csv(request):
    return _exportar_registros_csv(request, request.GET.get('tipo', 'todos'))


def _exportar_registros_csv(request, tipo):
    if tipo not in {'todos', 'asistieron', 'no_asistieron'}:
        tipo = 'todos'

    registros = Registro.objects.select_related('carrera', 'evento').filter(activo=True)
    if tipo == 'asistieron':
        registros = registros.filter(asistio=True)
    elif tipo == 'no_asistieron':
        registros = registros.filter(asistio=False)

    busqueda = request.GET.get('q', '').strip()
    registros = filtrar_por_busqueda(registros, busqueda)

    evento_id = request.GET.get('evento')
    carrera_ids = [value for value in request.GET.getlist('carrera') if value.isdigit()]
    semestres = [value for value in request.GET.getlist('semestre') if value.isdigit()]
    if evento_id and evento_id.isdigit():
        registros = registros.filter(evento_id=evento_id)
    if carrera_ids:
        registros = registros.filter(carrera_id__in=carrera_ids)
    if semestres:
        registros = registros.filter(semestre__in=semestres)

    nombres_archivo = {
        'todos': 'alumnos_todos.csv',
        'asistieron': 'alumnos_asistieron.csv',
        'no_asistieron': 'alumnos_no_asistieron.csv',
    }
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{nombres_archivo[tipo]}"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'Número de control', 'CURP', 'Nombre', 'Correo institucional', 'Lengua que habla',
        'Discapacidad', 'Otra discapacidad', 'Comunidad', 'Semestre', 'Carrera', 'Evento', 'Asistencia',
    ])
    for registro in registros.order_by('apellido_paterno', 'apellido_materno', 'nombre'):
        writer.writerow([
            registro.numero_control,
            registro.curp or '',
            registro.nombre_completo,
            registro.correo_institucional,
            registro.lengua_hablada,
            registro.get_discapacidad_display() if registro.discapacidad else '',
            registro.discapacidad_otra,
            registro.comunidad,
            registro.get_semestre_display(),
            registro.carrera.nombre,
            registro.evento.nombre,
            registro.asistencia_estado,
        ])
    return response


@login_required
def exportar_inasistencias(request):
    return _exportar_registros_csv(request, 'no_asistieron')


@login_required
def exportar_pdf(request):
    """
    Exportación de reportes a PDF nativo con xhtml2pdf y Gráficas de Pastel incrustadas.
    """
    from io import BytesIO
    from xhtml2pdf import pisa

    evento_id = request.GET.get('evento')
    carrera_ids = [c for c in request.GET.getlist('carrera') if c]
    semestres = [s for s in request.GET.getlist('semestre') if s]
    orden = request.GET.get('orden', 'az')
    
    registros = Registro.objects.select_related('carrera', 'evento').filter(activo=True)
    
    evento_nombre = "Todos los Eventos"
    carrera_nombre = "Todas las Carreras"
    semestre_nombre = "Todos los Semestres"
    orden_nombre = "Apellido Paterno (A-Z)"
    
    if evento_id:
        registros = registros.filter(evento_id=evento_id)
        try:
            evento_nombre = Evento.objects.get(id=evento_id).nombre
        except Evento.DoesNotExist:
            pass
            
    if carrera_ids:
        registros = registros.filter(carrera_id__in=carrera_ids)
        nombres = list(Carrera.objects.filter(id__in=carrera_ids).values_list('nombre', flat=True))
        if nombres:
            carrera_nombre = ", ".join(nombres)
            
    if semestres:
        registros = registros.filter(semestre__in=semestres)
        semestre_nombre = ", ".join([f"{s}° Sem" for s in semestres])
        
    # Ordenamiento por Apellidos
    if orden == 'az':
        registros = registros.order_by('apellido_paterno', 'apellido_materno', 'nombre')
        orden_nombre = "Apellido Paterno (A - Z)"
    elif orden == 'za':
        registros = registros.order_by('-apellido_paterno', '-apellido_materno', '-nombre')
        orden_nombre = "Apellido Paterno (Z - A)"
    elif orden == 'antiguos':
        registros = registros.order_by('fecha_registro')
        orden_nombre = "Fecha de Registro (Más antiguo primero)"
    else:
        registros = registros.order_by('-fecha_registro')
        orden_nombre = "Fecha de Registro (Más reciente primero)"
        
    # Datos para gráficas de pastel (agrupamiento limpio sin order_by de tabla)
    carreras_data = registros.order_by().values('carrera__nombre').annotate(total=Count('id')).order_by('-total')
    labels_carrera = [c['carrera__nombre'] for c in carreras_data]
    data_carrera = [c['total'] for c in carreras_data]
    colores_carrera = [CARRERA_COLOR_MAP.get(name, '#64748b') for name in labels_carrera]
    chart_carrera_b64 = generar_grafica_pastel(labels_carrera, data_carrera, "Distribución por Carrera", custom_colors=colores_carrera)
    
    semestres_data = registros.order_by().values('semestre').annotate(total=Count('id')).order_by('semestre')
    labels_semestre = [f"{s['semestre']}° Sem" for s in semestres_data]
    data_semestre = [s['total'] for s in semestres_data]
    chart_semestre_b64 = generar_grafica_pastel(labels_semestre, data_semestre, "Distribución por Semestre")

    context = {
        'registros': registros,
        'evento_nombre': evento_nombre,
        'carrera_nombre': carrera_nombre,
        'semestre_nombre': semestre_nombre,
        'orden_nombre': orden_nombre,
        'chart_carrera_b64': chart_carrera_b64,
        'chart_semestre_b64': chart_semestre_b64,
        'total': registros.count(),
        'request': request,
    }
    
    html_string = render_to_string('registros/reporte_pdf.html', context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="reporte_registros.pdf"'
        return response
    return HttpResponse("Error al generar el PDF", status=500)


@login_required
def agregar_carrera(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_carrera')
        if nombre:
            carrera, _ = Carrera.objects.get_or_create(nombre=nombre)
            if not carrera.activa:
                carrera.activa = True
                carrera.save(update_fields=['activa'])
            messages.success(request, f"¡Carrera '{nombre}' agregada a la base de datos!")
        else:
            messages.error(request, "El nombre de la carrera no puede estar vacío.")
    return redirect('dashboard')


@login_required
def eliminar_carrera(request, carrera_id):
    if request.method == 'POST':
        carrera = get_object_or_404(Carrera, id=carrera_id)
        try:
            carrera.delete()
            messages.success(request, "Carrera eliminada exitosamente.")
        except Exception as e:
            messages.error(request, "No se puede eliminar la carrera porque tiene estudiantes inscritos. Si deseas eliminarla, primero debes remover los registros de estos estudiantes.")
    return redirect('dashboard')


@login_required
def agregar_evento(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_evento', '').strip()
        fecha = request.POST.get('fecha_evento')
        if nombre and fecha:
            try:
                evento = Evento(
                    nombre=nombre,
                    fecha=fecha,
                    activo=True,
                )
                evento.full_clean()
                evento.save()
                messages.success(request, f"Fantástico. El evento '{nombre}' acaba de abrirse al público.")
            except ValidationError as error:
                messages.error(request, f"No se pudo guardar el evento: {' '.join(error.messages)}")
        else:
            messages.error(request, "Debes completar el nombre y la fecha del evento para habilitarlo.")
    return redirect('dashboard')


@login_required
def eliminar_evento(request, evento_id):
    if request.method == 'POST':
        evento = get_object_or_404(Evento, id=evento_id)
        try:
            evento.delete()
            messages.success(request, "El evento ha sido borrado del sistema exitosamente.")
        except Exception as e:
            messages.error(request, "No se puede eliminar el evento porque ya cuenta con alumnos inscritos. Para poder borrarlo, primero debes remover los registros de estudiantes asociados.")
    return redirect('dashboard')


@login_required
def eliminar_registro(request, registro_id):
    if request.method == 'POST':
        registro = get_object_or_404(Registro, id=registro_id)
        registro.activo = False
        registro.save()
        messages.success(request, f"El registro de '{registro.nombre_completo}' se movió a la Papelera de Reciclaje. Puedes restaurarlo cuando gustes.")
    return redirect('dashboard')


@login_required
def restaurar_registro(request, registro_id):
    if request.method == 'POST':
        registro = get_object_or_404(Registro, id=registro_id)
        registro.activo = True
        registro.save()
        messages.success(request, f"¡El registro de '{registro.nombre_completo}' ha sido restaurado exitosamente!")
    return redirect('dashboard')


@login_required
def eliminar_definitivo(request, registro_id):
    if request.method == 'POST':
        registro = get_object_or_404(Registro, id=registro_id)
        nombre = registro.nombre_completo
        registro.delete()  # Eliminación física definitiva de la base de datos
        messages.success(request, f"El registro de '{nombre}' fue eliminado permanentemente de la base de datos.")
    return redirect('dashboard')
