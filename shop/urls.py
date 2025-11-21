from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Páginas principales
    path('', views.home, name='home'),
    path('productos/', views.products_list, name='products_list'),
    path('productos/<slug:slug>/', views.product_detail, name='product_detail'),
    
    # Carrito
    path('carrito/', views.cart_view, name='cart'),
    path('carrito/agregar/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('carrito/actualizar/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('carrito/eliminar/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('carrito/limpiar/', views.clear_cart, name='clear_cart'),
    path('carrito/aplicar-cupon/', views.apply_coupon, name='apply_coupon'),
    path('carrito/checkout/', views.checkout, name='checkout'),
    
    # Pedidos
    path('pedido/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Autenticación
    path('registro/', views.register_view, name='register'),
    path('iniciar-sesion/', views.login_view, name='login'),
    path('cerrar-sesion/', views.logout_view, name='logout'),
    
    # Contacto
    path('contacto/', views.contact_view, name='contact'),
]

