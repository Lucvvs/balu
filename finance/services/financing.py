"""Aporte de capital y préstamos. No son ventas ni resultado operativo."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from finance.models import FinancialAccount, FinancialMovement, Financing
from finance.money import ZERO, quantize_clp


class FinancingError(ValueError):
    pass


def _require_account(account: FinancialAccount) -> FinancialAccount:
    if account is None or not account.is_active:
        raise FinancingError('Elige una cuenta de tesorería activa.')
    return account


@transaction.atomic
def register_contribution(*, account, amount, occurred_on, counterparty, notes='', user=None) -> Financing:
    account = _require_account(account)
    amount = quantize_clp(amount)
    if amount <= ZERO:
        raise FinancingError('El aporte debe ser mayor a 0.')
    name = (counterparty or '').strip()
    if not name:
        raise FinancingError('Indica quién hace el aporte.')
    financing = Financing.objects.create(
        kind=Financing.Kind.CONTRIBUTION,
        counterparty=name,
        principal=amount,
        account=account,
        occurred_on=occurred_on or timezone.localdate(),
        notes=(notes or '').strip(),
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    FinancialMovement.objects.create(
        account=account,
        direction=FinancialMovement.Direction.IN,
        amount=amount,
        occurred_on=financing.occurred_on,
        movement_type=FinancialMovement.MovementType.CAPITAL_CONTRIBUTION,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.MANUAL,
        idempotency_key=f'financing:{financing.pk}:in',
        notes=f'Aporte de capital de {name}. No es venta.',
        created_by=financing.created_by,
        financing=financing,
    )
    return financing


@transaction.atomic
def register_loan(*, account, amount, occurred_on, counterparty, notes='', user=None) -> Financing:
    account = _require_account(account)
    amount = quantize_clp(amount)
    if amount <= ZERO:
        raise FinancingError('El préstamo debe ser mayor a 0.')
    name = (counterparty or '').strip()
    if not name:
        raise FinancingError('Indica el prestamista.')
    financing = Financing.objects.create(
        kind=Financing.Kind.LOAN,
        counterparty=name,
        principal=amount,
        account=account,
        occurred_on=occurred_on or timezone.localdate(),
        notes=(notes or '').strip(),
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    FinancialMovement.objects.create(
        account=account,
        direction=FinancialMovement.Direction.IN,
        amount=amount,
        occurred_on=financing.occurred_on,
        movement_type=FinancialMovement.MovementType.LOAN_IN,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.MANUAL,
        idempotency_key=f'financing:{financing.pk}:in',
        notes=f'Préstamo de {name}. Es pasivo, no ingreso operativo.',
        created_by=financing.created_by,
        financing=financing,
    )
    return financing


@transaction.atomic
def repay_loan(*, financing: Financing, account, amount, occurred_on, notes='', user=None) -> FinancialMovement:
    financing = Financing.objects.select_for_update().get(pk=financing.pk)
    if financing.kind != Financing.Kind.LOAN:
        raise FinancingError('Solo se amortiza un préstamo, no un aporte.')
    account = _require_account(account)
    amount = quantize_clp(amount)
    if amount <= ZERO:
        raise FinancingError('El pago debe ser mayor a 0.')
    outstanding = financing.outstanding()
    if amount > outstanding:
        raise FinancingError(f'El saldo pendiente es {outstanding}. No se puede pagar de más.')
    occurred = occurred_on or timezone.localdate()
    seq = financing.movements.filter(
        movement_type=FinancialMovement.MovementType.LOAN_REPAYMENT,
    ).count() + 1
    return FinancialMovement.objects.create(
        account=account,
        direction=FinancialMovement.Direction.OUT,
        amount=amount,
        occurred_on=occurred,
        movement_type=FinancialMovement.MovementType.LOAN_REPAYMENT,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.MANUAL,
        idempotency_key=f'financing:{financing.pk}:repay:{seq}',
        notes=(notes or '').strip() or f'Pago de préstamo a {financing.counterparty}.',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        financing=financing,
    )
