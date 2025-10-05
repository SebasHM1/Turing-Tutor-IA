
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps
from .models import UserRole

def student_required(view_func):
    """
    Decorador para vistas que solo deben ser accesibles por usuarios
    con el rol de 'Student'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Asume que @login_required ya se ha aplicado,
        # por lo que request.user siempre existe.
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role != UserRole.STUDENT:
            # Si un profesor o admin intenta acceder, lo redirigimos a su propio dashboard.
            # O podrías lanzar un error PermissionDenied si lo prefieres.
            if request.user.role == UserRole.TEACHER:
                return redirect('teachers:dashboard')
            # Para cualquier otro caso, redirigir al login o a una página de error.
            raise PermissionDenied("No tienes permiso para acceder a esta página.")

        return view_func(request, *args, **kwargs)
    return _wrapped_view