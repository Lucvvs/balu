from django.urls import path

from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.resumen, name='resumen'),
    path('ingresos/ventas/', views.sales_lines, name='sales_lines'),
    path('ingresos/ventas/<int:item_id>/', views.sales_line_detail, name='sales_line_detail'),
    path('ingresos/financiamiento/', views.coming_soon, {'section': 'financing'}, name='financing'),
    path('gastos/', views.coming_soon, {'section': 'expenses'}, name='expenses'),
    path('saldos/', views.coming_soon, {'section': 'balances'}, name='balances'),
    path('inventario/', views.coming_soon, {'section': 'inventory'}, name='inventory'),
]
