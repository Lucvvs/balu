from .models import Cart


def cart_context(request):
    """Context processor para obtener el carrito del usuario/sesión"""
    cart = None
    cart_items_count = 0
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items_count = cart.get_total_items()
    elif request.session.session_key:
        try:
            cart = Cart.objects.get(session_key=request.session.session_key)
            cart_items_count = cart.get_total_items()
        except Cart.DoesNotExist:
            pass
    
    return {
        'cart': cart,
        'cart_items_count': cart_items_count,
    }

