from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .access import (
    FINANCE_CATALOG_PERM,
    FINANCE_EXPENSE_PERM,
    FINANCE_FINANCING_PERM,
    FINANCE_MANUAL_SALE_PERM,
    FINANCE_PURCHASES_PERM,
    user_can_access_finance,
    user_has_finance_perm,
)


def finance_view_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_can_access_finance(request.user):
            messages.error(request, 'No tienes permisos para acceder al módulo Finanzas.')
            return redirect('shop:home')
        return view(request, *args, **kwargs)
    return wrapped


def finance_catalog_required(view):
    @finance_view_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_has_finance_perm(request.user, FINANCE_CATALOG_PERM):
            messages.error(request, 'No tienes permiso para gestionar el catálogo.')
            return redirect('finance:inventory')
        return view(request, *args, **kwargs)
    return wrapped


def finance_manual_sale_required(view):
    @finance_view_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_has_finance_perm(request.user, FINANCE_MANUAL_SALE_PERM):
            messages.error(request, 'No tienes permiso para registrar una venta física.')
            return redirect('finance:sales_lines')
        return view(request, *args, **kwargs)
    return wrapped


def finance_financing_required(view):
    @finance_view_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_has_finance_perm(request.user, FINANCE_FINANCING_PERM):
            messages.error(request, 'No tienes permiso para gestionar financiamiento.')
            return redirect('finance:sales_lines')
        return view(request, *args, **kwargs)
    return wrapped


def finance_purchases_required(view):
    @finance_view_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_has_finance_perm(request.user, FINANCE_PURCHASES_PERM):
            messages.error(request, 'No tienes permiso para gestionar compras.')
            return redirect('finance:purchases')
        return view(request, *args, **kwargs)
    return wrapped


def finance_expense_required(view):
    @finance_view_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not user_has_finance_perm(request.user, FINANCE_EXPENSE_PERM):
            messages.error(request, 'No tienes permiso para registrar gastos.')
            return redirect('finance:expenses')
        return view(request, *args, **kwargs)
    return wrapped
