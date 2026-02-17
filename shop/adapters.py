from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

# Parche simple: interceptar el acceso a USERNAME_VALIDATORS para evitar el error
# cuando el modelo de usuario no tiene campo username
import allauth.account.app_settings as allauth_settings

# Guardar el descriptor original
_original_username_validators = type(allauth_settings._app_settings).__dict__.get('USERNAME_VALIDATORS')

# Crear un nuevo descriptor que capture la excepción
class SafeUsernameValidators:
    def __get__(self, obj, objtype=None):
        try:
            # Intentar obtener los validadores originales
            if _original_username_validators:
                return _original_username_validators.__get__(obj, objtype)
        except:
            # Si falla (porque no hay campo username), retornar lista vacía
            pass
        return []

# Reemplazar el descriptor
type(allauth_settings._app_settings).USERNAME_VALIDATORS = SafeUsernameValidators()


class CustomAccountAdapter(DefaultAccountAdapter):
    """Adaptador personalizado para manejar usuarios sin username"""
    
    def is_open_for_signup(self, request):
        """Permitir registro"""
        return True
    
    def clean_username(self, username, shallow=False):
        """Sobrescribir para evitar validación de username cuando no existe el campo"""
        # Como no usamos username, simplemente retornamos el valor sin validar
        # Esto evita que django-allauth intente acceder al campo username que no existe
        # IMPORTANTE: No llamamos a super() porque eso intentaría validar usando USERNAME_VALIDATORS
        # que a su vez intenta acceder al campo username del modelo
        return username or ''
    
    def generate_username(self, form):
        """Sobrescribir para no generar username, usar email en su lugar"""
        # No generar username, retornar None o email
        return None
    
    def get_user_display(self, user):
        """Retornar el display name del usuario para compatibilidad con django-allauth"""
        # Usar get_full_name si está disponible, sino email
        if hasattr(user, 'get_full_name'):
            name = user.get_full_name()
            if name:
                return name
        # Si no hay nombre completo, usar email
        return user.email if hasattr(user, 'email') else str(user)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptador personalizado para cuentas sociales sin username"""
    
    def pre_social_login(self, request, sociallogin):
        """Se ejecuta antes de hacer login con cuenta social"""
        # Si el usuario ya existe, simplemente conectarlo
        if sociallogin.is_existing:
            return
        
        # Si hay un usuario con el mismo email, conectarlo
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0]
            from .models import CustomUser
            try:
                user = CustomUser.objects.get(email=email.email)
                sociallogin.connect(request, user)
            except CustomUser.DoesNotExist:
                pass
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """Permitir auto-signup para evitar que intente generar username"""
        return True
    
    def get_username(self, sociallogin):
        """Sobrescribir para no generar username, retornar None"""
        # No generar username, retornar None para evitar que django-allauth intente validarlo
        return None
    
    def populate_user(self, request, sociallogin, data):
        """Poblar el usuario con datos de la cuenta social"""
        from .models import CustomUser
        
        # Crear el usuario directamente sin usar el método base que puede intentar usar username
        user = CustomUser()
        
        # Asegurar que el email se use como identificador
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0]
            user.email = email.email
        elif data.get('email'):
            user.email = data.get('email')
        else:
            # Si no hay email, no podemos crear el usuario
            raise ValueError("Email es requerido para crear el usuario")
        
        # Obtener nombres de los datos
        if data.get('given_name'):
            user.first_name = data.get('given_name', '')
        elif data.get('first_name'):
            user.first_name = data.get('first_name', '')
        
        if data.get('family_name'):
            user.last_name = data.get('family_name', '')
        elif data.get('last_name'):
            user.last_name = data.get('last_name', '')
        
        # Si aún no hay nombre, usar el nombre completo o email
        if not user.first_name and not user.last_name:
            if data.get('name'):
                name_parts = data.get('name', '').split(' ', 1)
                user.first_name = name_parts[0] if name_parts else ''
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            elif user.email:
                # Usar la parte antes del @ como nombre temporal
                user.first_name = user.email.split('@')[0]
                user.last_name = ''
        
        # Asegurar que first_name y last_name no estén vacíos (son requeridos)
        if not user.first_name:
            user.first_name = user.email.split('@')[0]
        if not user.last_name:
            user.last_name = ''
        
        # Copiar otros campos que el método base podría establecer
        if hasattr(sociallogin, 'user') and sociallogin.user:
            # Copiar campos comunes si existen
            for field in ['is_active', 'is_staff', 'is_superuser']:
                if hasattr(sociallogin.user, field):
                    setattr(user, field, getattr(sociallogin.user, field, False))
        
        # IMPORTANTE: Asignar el usuario al sociallogin ANTES de que django-allauth intente generar username
        sociallogin.user = user
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """Guardar el usuario de la cuenta social"""
        user = sociallogin.user
        if not user.pk:
            # Si el usuario no tiene pk, es nuevo y necesita guardarse
            user.save()
        return user
