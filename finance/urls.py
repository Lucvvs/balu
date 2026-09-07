from django.urls import path

from . import catalog_views, expense_views, financing_views, pos_views, purchase_views, refund_views, shipment_views, views

app_name = 'finance'

urlpatterns = [
    path('', views.resumen, name='resumen'),
    path('ingresos/ventas/', views.sales_lines, name='sales_lines'),
    path('ingresos/ventas/nueva/', pos_views.pos_sale, name='pos_sale'),
    path('ingresos/ventas/<int:item_id>/', views.sales_line_detail, name='sales_line_detail'),
    path('ingresos/financiamiento/', financing_views.financing, name='financing'),
    path('ingresos/devoluciones/', refund_views.refunds, name='refunds'),
    path('gastos/', expense_views.expenses, name='expenses'),
    path('gastos/envios/', shipment_views.shipments, name='shipments'),
    path('saldos/', views.balances, name='balances'),
    path('compras/', purchase_views.purchases, name='purchases'),
    path('inventario/', catalog_views.inventory, name='inventory'),
    path('inventario/nuevo/', catalog_views.product_create, name='product_create'),
    path('inventario/<int:product_id>/stock/', catalog_views.inventory_stock, name='inventory_stock'),
    path('inventario/<int:product_id>/', catalog_views.product_edit, name='product_edit'),
]
