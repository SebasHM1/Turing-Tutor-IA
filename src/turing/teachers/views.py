from django.shortcuts import render
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def teacher_dashboard(request):
    # Lógica y renderizado para el dashboard del profesor
    # Asegúrate de que el usuario sea realmente un profesor (opcional pero recomendado)
    if request.user.role != 'Teacher':
        return redirect('login') # O a una página de error
        
    return render(request, 'teachers/dashboard.html') # <-- Nota el nuevo path de la plantilla