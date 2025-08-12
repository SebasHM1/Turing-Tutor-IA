from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from users.models import UserRole

@login_required
def teacher_dashboard(request):
    if request.user.role != UserRole.TEACHER:
        return redirect('users:redirect_after_login')
    return render(request, 'teachers/dashboard.html')
