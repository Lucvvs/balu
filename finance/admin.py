from django.contrib import admin

from .models import (
    ExpenseCategory,
    FinancialAccount,
    FinancialMovement,
    Financing,
    MerchandisePurchase,
    OperationalExpense,
    OrderRefund,
    OrderRefundItem,
    OrderShipment,
    PaymentSettlement,
    PurchaseLine,
)


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'account_type',
        'ledger_role',
        'opening_balance',
        'opening_balance_date',
        'current_balance_display',
        'is_active',
    )
    list_filter = ('account_type', 'ledger_role', 'is_active')
    search_fields = ('name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'current_balance_display')
    fieldsets = (
        ('Cuenta', {
            'fields': ('name', 'account_type', 'ledger_role', 'is_active'),
        }),
        ('Saldo inicial', {
            'fields': ('opening_balance', 'opening_balance_date'),
            'description': (
                'El saldo actual no se edita: se deriva del saldo inicial '
                'más los movimientos del libro (cuando existan).'
            ),
        }),
        ('Auditoría', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at', 'current_balance_display'),
        }),
    )

    def current_balance_display(self, obj):
        if not obj.pk:
            return '—'
        return f"${int(obj.get_current_balance()):,}".replace(',', '.')
    current_balance_display.short_description = 'Saldo actual (calculado)'

    def save_model(self, request, obj, form, change):
        if not change and obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PaymentSettlement)
class PaymentSettlementAdmin(admin.ModelAdmin):
    list_display = ('mp_payment_id', 'order', 'status', 'gross_amount', 'fee_amount', 'net_amount', 'settled_on', 'account')
    list_filter = ('status', 'settled_on')
    search_fields = ('mp_payment_id', 'order__order_number')
    readonly_fields = (
        'payment', 'order', 'account', 'gross_amount', 'fee_amount', 'net_amount',
        'status', 'settled_on', 'money_release_date', 'mp_payment_id', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Financing)
class FinancingAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'kind', 'counterparty', 'principal', 'account', 'outstanding_display')
    list_filter = ('kind', 'occurred_on')
    search_fields = ('counterparty', 'notes')
    readonly_fields = (
        'kind', 'counterparty', 'principal', 'account', 'occurred_on',
        'notes', 'created_at', 'created_by', 'outstanding_display',
    )

    def outstanding_display(self, obj):
        if obj.kind != Financing.Kind.LOAN:
            return '—'
        return f"${int(obj.outstanding()):,}".replace(',', '.')
    outstanding_display.short_description = 'Saldo pendiente'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FinancialMovement)
class FinancialMovementAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'account', 'direction', 'amount', 'movement_type', 'status', 'idempotency_key')
    list_filter = ('direction', 'status', 'movement_type', 'occurred_on')
    search_fields = ('idempotency_key', 'notes')
    readonly_fields = (
        'account', 'direction', 'amount', 'occurred_on', 'movement_type', 'status', 'origin',
        'idempotency_key', 'payment', 'settlement', 'order', 'financing', 'purchase', 'expense', 'shipment', 'refund', 'created_at', 'updated_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0
    can_delete = False
    readonly_fields = (
        'product', 'product_variant', 'product_name', 'variant_label', 'sku_snapshot',
        'quantity', 'unit_cost_net', 'unit_cost_gross', 'line_net', 'line_gross', 'line_vat',
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MerchandisePurchase)
class MerchandisePurchaseAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'supplier', 'account', 'gross_total', 'updates_stock', 'updates_catalog_cost')
    list_filter = ('updates_stock', 'updates_catalog_cost', 'is_vat_affected', 'occurred_on')
    search_fields = ('supplier', 'notes')
    inlines = [PurchaseLineInline]
    readonly_fields = (
        'supplier', 'account', 'occurred_on', 'updates_stock', 'updates_catalog_cost',
        'is_vat_affected', 'gross_total', 'net_total', 'vat_credit', 'notes',
        'created_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'is_active', 'sort_order')
    list_filter = ('kind', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(OperationalExpense)
class OperationalExpenseAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'category', 'description', 'vendor', 'account', 'gross_amount', 'net_amount')
    list_filter = ('category__kind', 'is_vat_affected', 'occurred_on')
    search_fields = ('description', 'vendor', 'notes')
    readonly_fields = (
        'category', 'vendor', 'description', 'account', 'occurred_on', 'is_vat_affected',
        'gross_amount', 'net_amount', 'vat_credit', 'notes', 'created_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderShipment)
class OrderShipmentAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'order', 'carrier', 'charged_amount', 'actual_cost', 'assumed_cost')
    search_fields = ('order__order_number', 'carrier', 'tracking_code')
    readonly_fields = (
        'order', 'account', 'carrier', 'tracking_code', 'charged_amount', 'actual_cost',
        'assumed_cost', 'occurred_on', 'notes', 'created_at', 'updated_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OrderRefundItemInline(admin.TabularInline):
    model = OrderRefundItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'order_item', 'quantity', 'gross_amount', 'net_amount', 'vat_amount',
        'cogs_amount', 'commission_amount', 'shipping_assumed_amount',
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrderRefund)
class OrderRefundAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'order', 'gross_amount', 'net_amount', 'restores_stock')
    list_filter = ('restores_stock', 'occurred_on')
    search_fields = ('order__order_number', 'notes')
    inlines = [OrderRefundItemInline]
    readonly_fields = (
        'order', 'account', 'occurred_on', 'restores_stock', 'gross_amount', 'net_amount',
        'vat_amount', 'cogs_amount', 'notes', 'created_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
