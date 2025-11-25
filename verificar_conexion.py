"""
Script para verificar la conexión a la base de datos de Render
sin necesitar psql instalado
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'motomoto.settings')
django.setup()

from django.db import connection
from django.conf import settings

print("=" * 50)
print("Verificando conexión a la base de datos...")
print("=" * 50)
print()

# Mostrar configuración
db_config = settings.DATABASES['default']
print(f"Motor de base de datos: {db_config['ENGINE']}")
if 'NAME' in db_config:
    print(f"Base de datos: {db_config['NAME']}")
if 'HOST' in db_config:
    print(f"Host: {db_config['HOST']}")
if 'PORT' in db_config:
    print(f"Puerto: {db_config['PORT']}")
print()

# Intentar conectar
try:
    print("Intentando conectar...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print("✅ Conexión exitosa!")
        print()
        print("Versión de PostgreSQL:")
        print(version[0])
        print()
        print("=" * 50)
        print("✅ La conexión está funcionando correctamente")
        print("=" * 50)
        sys.exit(0)
except Exception as e:
    print("❌ Error al conectar:")
    print(str(e))
    print()
    print("Posibles causas:")
    print("- DATABASE_URL incorrecta en .env")
    print("- Base de datos no está activa en Render")
    print("- Firewall bloqueando la conexión")
    print("- Credenciales incorrectas")
    sys.exit(1)





