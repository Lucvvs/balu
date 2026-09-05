"""Autorización del módulo Finanzas. No confiar solo en ocultar enlaces."""

FINANCE_VIEW_PERM = 'finance.view_finance'
FINANCE_MANUAL_SALE_PERM = 'finance.add_manual_sale'
FINANCE_EXPENSE_PERM = 'finance.register_expense'
FINANCE_FINANCING_PERM = 'finance.manage_financing'
FINANCE_ACCOUNTS_PERM = 'finance.manage_accounts'
FINANCE_PURCHASES_PERM = 'finance.manage_purchases'
FINANCE_CATALOG_PERM = 'finance.manage_catalog'


def user_can_access_finance(user) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if not user.is_staff:
        return False
    return user.has_perm(FINANCE_VIEW_PERM)


def user_has_finance_perm(user, perm: str) -> bool:
    return user_can_access_finance(user) and user.has_perm(perm)
