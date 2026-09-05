"""Gastos operativos. No son compras de mercadería ni ventas."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from finance.models import ExpenseCategory, FinancialAccount, FinancialMovement, OperationalExpense
from finance.money import ZERO, quantize_clp, split_gross_vat


class ExpenseError(ValueError):
    pass


def _require_account(account: FinancialAccount) -> FinancialAccount:
    if account is None or not account.is_active:
        raise ExpenseError('Elige una cuenta de tesorería activa.')
    return account


def _unique_category_slug(name: str) -> str:
    base = slugify(name) or 'categoria'
    slug = base
    n = 2
    while ExpenseCategory.objects.filter(slug=slug).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


@transaction.atomic
def create_expense_category(*, name: str, kind: str, user=None) -> ExpenseCategory:
    label = (name or '').strip()
    if not label:
        raise ExpenseError('Indica el nombre de la categoría.')
    if kind not in ExpenseCategory.Kind.values:
        raise ExpenseError('Elige un grupo válido: infraestructura, servicios, publicidad u otros.')
    if ExpenseCategory.objects.filter(name__iexact=label).exists():
        raise ExpenseError('Ya existe una categoría con ese nombre.')
    return ExpenseCategory.objects.create(
        name=label,
        slug=_unique_category_slug(label),
        kind=kind,
        is_active=True,
        sort_order=ExpenseCategory.objects.count() * 10 + 10,
    )


@transaction.atomic
def register_expense(
    *,
    category,
    account,
    vendor: str,
    description: str,
    amount,
    occurred_on=None,
    is_vat_affected: bool = True,
    notes: str = '',
    user=None,
) -> OperationalExpense:
    """
    Paga un gasto operativo. Baja tesorería y suma opex.

    El opex es el neto si hay IVA; el bruto es lo que sale de la cuenta.
    No crea ventas ni compras de mercadería.
    """
    account = _require_account(account)
    if category is None or not category.is_active:
        raise ExpenseError('Elige una categoría de gasto activa.')
    payee = (vendor or '').strip()
    if not payee:
        raise ExpenseError('Indica a quién se le paga.')
    detail = (description or '').strip()
    if not detail:
        raise ExpenseError('Describe el gasto.')
    gross = quantize_clp(amount)
    if gross <= ZERO:
        raise ExpenseError('El monto debe ser mayor a 0.')
    net, vat = split_gross_vat(gross, is_vat_affected=is_vat_affected)
    expense = OperationalExpense.objects.create(
        category=category,
        vendor=payee,
        description=detail,
        account=account,
        occurred_on=occurred_on or timezone.localdate(),
        is_vat_affected=is_vat_affected,
        gross_amount=gross,
        net_amount=net,
        vat_credit=vat,
        notes=(notes or '').strip(),
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    FinancialMovement.objects.create(
        account=account,
        direction=FinancialMovement.Direction.OUT,
        amount=gross,
        occurred_on=expense.occurred_on,
        movement_type=FinancialMovement.MovementType.EXPENSE,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.MANUAL,
        idempotency_key=f'expense:{expense.pk}:out',
        notes=f'Gasto {category.name}: {detail}. No es compra de mercadería.',
        created_by=expense.created_by,
        expense=expense,
    )
    return expense
