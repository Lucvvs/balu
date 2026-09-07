from finance.access import (
    FINANCE_CATALOG_PERM,
    FINANCE_EXPENSE_PERM,
    FINANCE_FINANCING_PERM,
    FINANCE_MANUAL_SALE_PERM,
    FINANCE_PURCHASES_PERM,
    user_has_finance_perm,
)
from finance.models import FinancialAccount


def sales_querystring(filters: dict) -> str:
    parts = [
        f"date_from={filters['date_from'].isoformat()}",
        f"date_to={filters['date_to'].isoformat()}",
    ]
    if filters['channel']:
        parts.append(f"channel={filters['channel']}")
    if filters['account_id']:
        parts.append(f"account={filters['account_id']}")
    return '&'.join(parts)


def filter_context(request, filters: dict) -> dict:
    return {
        'date_from': filters['date_from'].isoformat(),
        'date_to': filters['date_to'].isoformat(),
        'date_from_obj': filters['date_from'],
        'date_to_obj': filters['date_to'],
        'channel': filters['channel'],
        'account_id': filters['account_id'] or '',
        'accounts': FinancialAccount.objects.filter(is_active=True).order_by('name'),
        'can_manage_catalog': user_has_finance_perm(request.user, FINANCE_CATALOG_PERM),
        'can_add_manual_sale': user_has_finance_perm(request.user, FINANCE_MANUAL_SALE_PERM),
        'can_manage_financing': user_has_finance_perm(request.user, FINANCE_FINANCING_PERM),
        'can_manage_purchases': user_has_finance_perm(request.user, FINANCE_PURCHASES_PERM),
        'can_register_expense': user_has_finance_perm(request.user, FINANCE_EXPENSE_PERM),
    }
