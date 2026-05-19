"""
Catálogo de productos en PDF (admin): rejilla tipo folleto impreso, A4.
Las imágenes pasan por Pillow (RGBA/WebP → RGB PNG) para compatibilidad con ReportLab.
"""
from shop.catalog_pdf.builder import build_catalog_pdf_bytes, build_catalog_pdf_file
from shop.catalog_pdf.products import filter_products_for_catalog_pdf

__all__ = [
    "build_catalog_pdf_bytes",
    "build_catalog_pdf_file",
    "filter_products_for_catalog_pdf",
]
