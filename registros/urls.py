from django.urls import path
from . import views

urlpatterns = [
    path('', views.registro_publico, name='registro_publico'),
    path('dashboard/', views.dashboard_admin, name='dashboard'),
    path('dashboard/configuracion/whatsapp/', views.configurar_whatsapp, name='configurar_whatsapp'),
    path('dashboard/registros/<int:registro_id>/asistencia/', views.actualizar_asistencia, name='actualizar_asistencia'),
    path('dashboard/exportar-registros/', views.exportar_registros_csv, name='exportar_registros_csv'),
    path('dashboard/exportar-inasistencias/', views.exportar_inasistencias, name='exportar_inasistencias'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('dashboard/carreras/agregar/', views.agregar_carrera, name='agregar_carrera'),
    path('dashboard/carreras/eliminar/<int:carrera_id>/', views.eliminar_carrera, name='eliminar_carrera'),
    path('dashboard/eventos/agregar/', views.agregar_evento, name='agregar_evento'),
    path('dashboard/eventos/eliminar/<int:evento_id>/', views.eliminar_evento, name='eliminar_evento'),
    path('dashboard/registros/eliminar/<int:registro_id>/', views.eliminar_registro, name='eliminar_registro'),
    path('dashboard/registros/restaurar/<int:registro_id>/', views.restaurar_registro, name='restaurar_registro'),
    path('dashboard/registros/eliminar-definitivo/<int:registro_id>/', views.eliminar_definitivo, name='eliminar_definitivo'),
]
