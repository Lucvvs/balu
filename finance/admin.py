from django.contrib import admin

from .models import FinancialAccount, FinancialMovement, PaymentSettlement


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


@admin.register(FinancialMovement)
class FinancialMovementAdmin(admin.ModelAdmin):
    list_display = ('occurred_on', 'account', 'direction', 'amount', 'movement_type', 'status', 'idempotency_key')
    list_filter = ('direction', 'status', 'movement_type', 'occurred_on')
    search_fields = ('idempotency_key', 'notes')
    readonly_fields = (
        'account', 'direction', 'amount', 'occurred_on', 'movement_type', 'status', 'origin',
        'idempotency_key', 'payment', 'settlement', 'order', 'created_at', 'updated_at', 'created_by',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
