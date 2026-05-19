"""Filtrado y orden de productos para el catálogo PDF."""
from typing import Iterable

from django.db.models import Exists, OuterRef, Q, QuerySet

from shop.catalog_pdf.constants import CATALOG_CATEGORY_ORDER, CATALOG_CATEGORY_OTROS


def filter_products_for_catalog_pdf(products: Iterable | QuerySet):
    """
    Solo productos vendibles: stock > 0 sin variantes, o al menos una variante con stock.
    Coincide con Product.is_available_for_purchase().
    """
    from shop.models import ProductVariant

    variant_in_stock = ProductVariant.objects.filter(
        product_id=OuterRef("pk"),
        stock__gt=0,
    )
    has_variants = ProductVariant.objects.filter(product_id=OuterRef("pk"))
    available = Q(Exists(variant_in_stock)) | (Q(stock__gt=0) & ~Q(Exists(has_variants)))

    if isinstance(products, QuerySet):
        return products.filter(available)
    return [p for p in products if p.is_available_for_purchase()]


def catalog_category_sort_key(product) -> tuple:
    cat = product.category
    cat_name = (cat.name if cat else "").strip().lower()
    cat_slug = (cat.slug if cat else "").strip().lower()
    ident = cat_slug or cat_name

    for idx, label in enumerate(CATALOG_CATEGORY_ORDER):
        if ident == label or cat_name == label:
            return (0, idx, product.name.lower())

    if ident == CATALOG_CATEGORY_OTROS or cat_name == CATALOG_CATEGORY_OTROS:
        return (0, len(CATALOG_CATEGORY_ORDER), product.name.lower())

    return (1, cat_name, product.name.lower())
