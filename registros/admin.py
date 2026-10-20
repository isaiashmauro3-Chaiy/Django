from django.contrib import admin
from .models import Carrera, ConfiguracionSitio, Evento, Registro

@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre',)

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha', 'cupo_maximo', 'activo')
    list_filter = ('activo', 'fecha')
    search_fields = ('nombre',)

@admin.register(ConfiguracionSitio)
class ConfiguracionSitioAdmin(admin.ModelAdmin):
    list_display = ('enlace_whatsapp',)

    def has_add_permission(self, request):
        return not ConfiguracionSitio.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('numero_control', 'nombre_completo', 'correo_institucional', 'carrera', 'evento', 'fecha_registro')
    list_filter = ('evento', 'carrera', 'semestre')
    search_fields = ('numero_control', 'nombre_completo', 'correo_institucional')
