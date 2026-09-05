from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .access import user_can_access_finance


def finance_view_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_can_access_finance(request.user):
            messages.error(request, 'No tienes permisos para acceder al módulo Finanzas.')
            return redirect('shop:home')
        return view(request, *args, **kwargs)
    return wrapped
