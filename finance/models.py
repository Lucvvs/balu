from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .money import ZERO, to_decimal


class FinancialAccount(models.Model):
    """
    Cuenta de tesorería (caja, banco o saldo digital).

    El saldo actual se DERIVA: saldo inicial + entradas - salidas.
    Nunca se edita un campo de saldo corriente.
    """

    class AccountType(models.TextChoices):
        CASH = 'cash', 'Caja'
        BANK = 'bank', 'Banco'
        DIGITAL = 'digital', 'Saldo digital'

    name = models.CharField(max_length=120, verbose_name='Nombre')
    account_type = models.CharField(
        max_length=16,
        choices=AccountType.choices,
        verbose_name='Tipo',
        db_index=True,
    )
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        default=0,
        verbose_name='Saldo inicial (CLP)',
        help_text='Punto de partida. El saldo actual se calcula a partir de los movimientos.',
    )
    opening_balance_date = models.DateField(
        verbose_name='Fecha del saldo inicial',
    )
    is_active = models.BooleanField(default=True, verbose_name='Activa', db_index=True)
    ledger_role = models.CharField(
        max_length=32,
        choices=[
            ('mp', 'Liquidaciones Mercado Pago'),
            ('bank_transfers', 'Transferencias bancarias'),
            ('cash', 'Caja efectivo'),
        ],
        blank=True,
        null=True,
        unique=True,
        verbose_name='Rol en tesorería',
        help_text='Como máximo una cuenta por rol. Las liquidaciones MP usan el rol Mercado Pago.',
    )
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última modificación')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_financial_accounts',
        verbose_name='Creada por',
    )

    class Meta:
        verbose_name = 'Cuenta de tesorería'
        verbose_name_plural = 'Cuentas de tesorería'
        ordering = ['account_type', 'name']
        constraints = [
            models.CheckConstraint(
                condition=Q(name__gt=''),
                name='finance_account_name_not_empty',
            ),
        ]
        permissions = [
            ('view_finance', 'Puede ver el módulo Finanzas'),
            ('add_manual_sale', 'Puede registrar venta física'),
            ('register_expense', 'Puede registrar gastos'),
            ('manage_financing', 'Puede gestionar financiamiento'),
            ('manage_accounts', 'Puede gestionar cuentas de tesorería'),
            ('manage_purchases', 'Puede gestionar compras'),
            ('manage_catalog', 'Puede gestionar catálogo e inventario'),
        ]
        indexes = [
            models.Index(fields=['account_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_account_type_display()})'

    def clean(self):
        super().clean()
        if not (self.name or '').strip():
            raise ValidationError({'name': 'El nombre de la cuenta es obligatorio.'})
        if self.opening_balance_date is None:
            raise ValidationError({'opening_balance_date': 'Indica la fecha del saldo inicial.'})

    def get_current_balance(self) -> Decimal:
        """
        Saldo derivado.

        Incremento 1: aún no existen movimientos; el saldo es el inicial.
        Incremento 3: sumará entradas y restará salidas confirmadas del libro.
        """
        inflows = ZERO
        outflows = ZERO
        movements = getattr(self, 'movements', None)
        if movements is not None:
            from django.db.models import Sum

            confirmed = movements.filter(status='confirmed')
            inflows = to_decimal(
                confirmed.filter(direction='in').aggregate(total=Sum('amount'))['total']
            )
            outflows = to_decimal(
                confirmed.filter(direction='out').aggregate(total=Sum('amount'))['total']
            )
        return to_decimal(self.opening_balance) + inflows - outflows

    @classmethod
    def get_by_role(cls, role: str):
        return cls.objects.filter(ledger_role=role, is_active=True).first()


class PaymentSettlement(models.Model):
    """Dinero efectivamente disponible para MotoMoto (distinto del pago del cliente)."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente de liquidación'
        SETTLED = 'settled', 'Liquidado'
        VOIDED = 'voided', 'Anulado'

    payment = models.OneToOneField(
        'shop.Payment',
        on_delete=models.PROTECT,
        related_name='settlement',
        verbose_name='Pago',
    )
    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.PROTECT,
        related_name='settlements',
        verbose_name='Pedido',
    )
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='settlements',
        verbose_name='Cuenta destino',
    )
    gross_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Monto bruto (CLP)')
    fee_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Comisión real (CLP)')
    net_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Monto liquidado (CLP)')
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name='Estado',
    )
    settled_on = models.DateField(null=True, blank=True, verbose_name='Fecha de liquidación', db_index=True)
    money_release_date = models.DateField(null=True, blank=True, verbose_name='Fecha de liberación MP')
    mp_payment_id = models.CharField(max_length=100, verbose_name='MP Payment ID', db_index=True)
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Liquidación de pago'
        verbose_name_plural = 'Liquidaciones de pago'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['mp_payment_id'], name='unique_settlement_mp_payment_id'),
            models.CheckConstraint(condition=Q(gross_amount__gte=0), name='settlement_gross_gte_0'),
            models.CheckConstraint(condition=Q(fee_amount__gte=0), name='settlement_fee_gte_0'),
            models.CheckConstraint(condition=Q(net_amount__gte=0), name='settlement_net_gte_0'),
        ]

    def __str__(self):
        return f'Liquidación {self.mp_payment_id} ({self.get_status_display()})'


class FinancialMovement(models.Model):
    """Impacto en una cuenta. No reemplaza la venta, el gasto ni la liquidación."""

    class Direction(models.TextChoices):
        IN = 'in', 'Entrada'
        OUT = 'out', 'Salida'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        CONFIRMED = 'confirmed', 'Confirmado'
        VOIDED = 'voided', 'Anulado'

    class Origin(models.TextChoices):
        AUTOMATIC = 'automatic', 'Automático'
        MANUAL = 'manual', 'Manual'

    class MovementType(models.TextChoices):
        SALE_SETTLEMENT = 'sale_settlement', 'Liquidación de venta'
        MANUAL_ADJUSTMENT = 'manual_adjustment', 'Ajuste manual'

    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Cuenta',
    )
    direction = models.CharField(max_length=8, choices=Direction.choices, verbose_name='Dirección')
    amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Monto (CLP)')
    occurred_on = models.DateField(verbose_name='Fecha económica', db_index=True)
    movement_type = models.CharField(
        max_length=32,
        choices=MovementType.choices,
        db_index=True,
        verbose_name='Tipo',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_index=True,
        verbose_name='Estado',
    )
    origin = models.CharField(
        max_length=16,
        choices=Origin.choices,
        default=Origin.AUTOMATIC,
        verbose_name='Origen',
    )
    idempotency_key = models.CharField(max_length=120, unique=True, verbose_name='Clave de idempotencia')
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_financial_movements',
        verbose_name='Creado por',
    )
    payment = models.ForeignKey(
        'shop.Payment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='financial_movements',
        verbose_name='Pago',
    )
    settlement = models.ForeignKey(
        PaymentSettlement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='financial_movements',
        verbose_name='Liquidación',
    )
    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='financial_movements',
        verbose_name='Pedido',
    )

    class Meta:
        verbose_name = 'Movimiento de tesorería'
        verbose_name_plural = 'Movimientos de tesorería'
        ordering = ['-occurred_on', '-id']
        indexes = [
            models.Index(fields=['account', 'occurred_on']),
            models.Index(fields=['status', 'occurred_on']),
            models.Index(fields=['movement_type', 'occurred_on']),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name='movement_amount_gte_0'),
            models.CheckConstraint(condition=Q(idempotency_key__gt=''), name='movement_idempotency_not_empty'),
        ]

    def __str__(self):
        sign = '+' if self.direction == self.Direction.IN else '-'
        return f'{sign}${self.amount} {self.account} ({self.get_movement_type_display()})'

    def delete(self, *args, **kwargs):
        if self.status == self.Status.CONFIRMED:
            raise ValidationError('No se eliminan movimientos confirmados. Anúlalos para conservar la auditoría.')
        return super().delete(*args, **kwargs)

