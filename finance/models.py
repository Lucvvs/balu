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
        CAPITAL_CONTRIBUTION = 'capital_contribution', 'Aporte de capital'
        LOAN_IN = 'loan_in', 'Desembolso de préstamo'
        LOAN_REPAYMENT = 'loan_repayment', 'Pago de préstamo'
        PURCHASE = 'purchase', 'Compra de mercadería'
        EXPENSE = 'expense', 'Gasto operativo'
        SHIPMENT = 'shipment', 'Flete de envío'
        REFUND = 'refund', 'Devolución al cliente'

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
    financing = models.ForeignKey(
        'Financing',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='Financiamiento',
    )
    purchase = models.ForeignKey(
        'MerchandisePurchase',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='Compra',
    )
    expense = models.ForeignKey(
        'OperationalExpense',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='Gasto',
    )
    shipment = models.ForeignKey(
        'OrderShipment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='Envío',
    )
    refund = models.ForeignKey(
        'OrderRefund',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='Devolución',
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


class Financing(models.Model):
    """Aporte de capital o préstamo. No es venta ni gasto operativo."""

    class Kind(models.TextChoices):
        CONTRIBUTION = 'contribution', 'Aporte de capital'
        LOAN = 'loan', 'Préstamo'

    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True, verbose_name='Tipo')
    counterparty = models.CharField(max_length=160, verbose_name='Origen / prestamista')
    principal = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Monto original (CLP)')
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='financings',
        verbose_name='Cuenta destino',
    )
    occurred_on = models.DateField(verbose_name='Fecha', db_index=True)
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_financings',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Financiamiento'
        verbose_name_plural = 'Financiamientos'
        ordering = ['-occurred_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(principal__gt=0), name='financing_principal_gt_0'),
            models.CheckConstraint(condition=Q(counterparty__gt=''), name='financing_counterparty_not_empty'),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} {self.counterparty} ${self.principal}'

    def outstanding(self):
        if self.kind != self.Kind.LOAN:
            return ZERO
        from django.db.models import Sum

        repaid = to_decimal(
            self.movements.filter(
                movement_type=FinancialMovement.MovementType.LOAN_REPAYMENT,
                status=FinancialMovement.Status.CONFIRMED,
            ).aggregate(total=Sum('amount'))['total']
        )
        remaining = to_decimal(self.principal) - repaid
        return remaining if remaining > ZERO else ZERO


class MerchandisePurchase(models.Model):
    """Compra de mercadería. No es venta ni gasto operativo."""

    supplier = models.CharField(max_length=160, verbose_name='Proveedor')
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name='Cuenta que paga',
    )
    occurred_on = models.DateField(verbose_name='Fecha', db_index=True)
    updates_stock = models.BooleanField(
        default=True,
        verbose_name='Sumar al stock',
        help_text='Si está activo, las unidades compradas entran al inventario.',
    )
    updates_catalog_cost = models.BooleanField(
        default=True,
        verbose_name='Actualizar costo vigente',
        help_text='Costo estándar / último conocido. No recalcula ventas ya sincronizadas.',
    )
    is_vat_affected = models.BooleanField(default=True, verbose_name='Afecta a IVA')
    gross_total = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Total bruto (CLP)')
    net_total = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Total neto (CLP)')
    vat_credit = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='IVA crédito (CLP)')
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_purchases',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Compra de mercadería'
        verbose_name_plural = 'Compras de mercadería'
        ordering = ['-occurred_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(supplier__gt=''), name='purchase_supplier_not_empty'),
            models.CheckConstraint(condition=Q(gross_total__gte=0), name='purchase_gross_gte_0'),
        ]

    def __str__(self):
        return f'Compra {self.supplier} ${self.gross_total}'


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(
        MerchandisePurchase,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Compra',
    )
    product = models.ForeignKey(
        'shop.Product',
        on_delete=models.PROTECT,
        related_name='purchase_lines',
        verbose_name='Producto',
    )
    product_variant = models.ForeignKey(
        'shop.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_lines',
        verbose_name='Variante',
    )
    product_name = models.CharField(max_length=200, verbose_name='Producto (snapshot)')
    variant_label = models.CharField(max_length=64, blank=True, default='', verbose_name='Opción (snapshot)')
    sku_snapshot = models.CharField(max_length=64, blank=True, default='', verbose_name='SKU (snapshot)')
    quantity = models.IntegerField(verbose_name='Cantidad')
    unit_cost_net = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Costo unitario neto')
    unit_cost_gross = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Costo unitario bruto')
    line_net = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Neto línea')
    line_gross = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Bruto línea')
    line_vat = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='IVA línea')

    class Meta:
        verbose_name = 'Línea de compra'
        verbose_name_plural = 'Líneas de compra'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name='purchase_line_qty_gte_1'),
        ]

    def __str__(self):
        return f'{self.product_name} x{self.quantity}'


class ExpenseCategory(models.Model):
    """Categoría de gasto operativo. No incluye compras de mercadería."""

    class Kind(models.TextChoices):
        INFRASTRUCTURE = 'infrastructure', 'Infraestructura'
        SERVICES = 'services', 'Servicios'
        ADS = 'ads', 'Publicidad'
        OTHER = 'other', 'Otros'

    name = models.CharField(max_length=80, verbose_name='Nombre')
    slug = models.SlugField(max_length=80, unique=True, verbose_name='Slug')
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        db_index=True,
        verbose_name='Grupo',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Activa')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name = 'Categoría de gasto'
        verbose_name_plural = 'Categorías de gasto'
        ordering = ['sort_order', 'name']
        constraints = [
            models.CheckConstraint(condition=Q(name__gt=''), name='expense_category_name_not_empty'),
        ]

    def __str__(self):
        return self.name


class OperationalExpense(models.Model):
    """Gasto operativo (opex). No es compra de mercadería ni venta."""

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Categoría',
    )
    vendor = models.CharField(max_length=160, verbose_name='Proveedor / destinatario')
    description = models.CharField(max_length=200, verbose_name='Descripción')
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Cuenta que paga',
    )
    occurred_on = models.DateField(verbose_name='Fecha', db_index=True)
    is_vat_affected = models.BooleanField(default=True, verbose_name='Afecta a IVA')
    gross_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Total bruto (CLP)')
    net_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Neto (opex)')
    vat_credit = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='IVA crédito (CLP)')
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_expenses',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Gasto operativo'
        verbose_name_plural = 'Gastos operativos'
        ordering = ['-occurred_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(vendor__gt=''), name='expense_vendor_not_empty'),
            models.CheckConstraint(condition=Q(description__gt=''), name='expense_description_not_empty'),
            models.CheckConstraint(condition=Q(gross_amount__gt=0), name='expense_gross_gt_0'),
        ]

    def __str__(self):
        return f'{self.description} ${self.gross_amount}'


class OrderShipment(models.Model):
    """Fuente única del flete: cobrado al cliente vs costo real/asumido."""

    order = models.OneToOneField(
        'shop.Order',
        on_delete=models.PROTECT,
        related_name='shipment',
        verbose_name='Pedido',
    )
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='shipments',
        verbose_name='Cuenta que paga el flete',
    )
    carrier = models.CharField(max_length=120, blank=True, default='', verbose_name='Courier')
    tracking_code = models.CharField(max_length=80, blank=True, default='', verbose_name='Seguimiento')
    charged_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Cobrado al cliente')
    actual_cost = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Costo real (courier)')
    assumed_cost = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Costo asumido (margen)')
    occurred_on = models.DateField(verbose_name='Fecha', db_index=True)
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_shipments',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Envío'
        verbose_name_plural = 'Envíos'
        ordering = ['-occurred_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(charged_amount__gte=0), name='shipment_charged_gte_0'),
            models.CheckConstraint(condition=Q(actual_cost__gte=0), name='shipment_actual_gte_0'),
            models.CheckConstraint(condition=Q(assumed_cost__gte=0), name='shipment_assumed_gte_0'),
        ]

    def __str__(self):
        return f'Envío pedido {self.order_id} ${self.assumed_cost}'


class OrderRefund(models.Model):
    """Devolución. No borra ni reescribe la venta original."""

    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.PROTECT,
        related_name='refunds',
        verbose_name='Pedido',
    )
    account = models.ForeignKey(
        FinancialAccount,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='refunds',
        verbose_name='Cuenta que devuelve el dinero',
    )
    occurred_on = models.DateField(verbose_name='Fecha', db_index=True)
    restores_stock = models.BooleanField(default=True, verbose_name='Devolver stock')
    gross_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Bruto devuelto')
    net_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Neto devuelto')
    vat_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='IVA revertido')
    cogs_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Costo revertido')
    notes = models.TextField(blank=True, default='', verbose_name='Observaciones')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_refunds',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering = ['-occurred_on', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(gross_amount__gte=0), name='refund_gross_gte_0'),
        ]

    def __str__(self):
        return f'Devolución pedido {self.order_id} ${self.gross_amount}'


class OrderRefundItem(models.Model):
    refund = models.ForeignKey(
        OrderRefund,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Devolución',
    )
    order_item = models.ForeignKey(
        'shop.OrderItem',
        on_delete=models.PROTECT,
        related_name='refund_lines',
        verbose_name='Línea original',
    )
    quantity = models.IntegerField(verbose_name='Cantidad')
    gross_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Bruto')
    net_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Neto')
    vat_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='IVA')
    cogs_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Costo')
    commission_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Comisión revertida')
    shipping_assumed_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name='Flete revertido')

    class Meta:
        verbose_name = 'Línea de devolución'
        verbose_name_plural = 'Líneas de devolución'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name='refund_item_qty_gte_1'),
        ]

    def __str__(self):
        return f'Devolución {self.order_item_id} x{self.quantity}'


