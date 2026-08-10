# Envío a domicilio y envío especial

## 1. Efectivo no disponible con envío a domicilio

**Problema:** Se podía pagar en efectivo con envío a domicilio, aunque el despacho exige pago previo confirmado.

**Solución:** Al elegir domicilio se deshabilita Efectivo (UI + validación en form/checkout) y se muestra un aviso: el pedido se despacha una vez confirmado el pago. En retiro, Efectivo sigue disponible.

## 2. Envío especial por producto (gran volumen)

**Problema:** Productos grandes generaban envíos caros o mal calibrados con las tarifas globales por región.

**Solución:** En el admin, activar «Usar envío especial» y definir tarifas por región en el producto. Solo esos productos usan esas tarifas; el carrito cobra el máximo entre especiales (y el estándar si hay productos normales).
