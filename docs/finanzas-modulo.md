# Módulo Finanzas — bitácora breve de incrementos

## Incremento 1 — Cimientos

App `finance` con cuentas de tesorería (saldo derivado, no editable). El catálogo ganó SKU y costo vigente; el pedido, canal y estado financiero; cada `OrderItem` quedó listo para snapshots. El dinero se calcula con Decimal (CLP entero, IVA 19%, prorrateo que cierra al peso). Permisos `finance.view_finance` y afines; el storefront no cambió. Tests de IVA, prorrateo y saldo inicial.

## Incremento 2 — Sync de venta

Al crear un pedido web, `sync_sale_from_order` congela por línea SKU, precio lista, venta bruta/neta, IVA y costo histórico. El descuento del pedido se reparte proporcional al neto; el envío cobrado también, sin duplicar el monto. Re-ejecutar el sync no pisa el costo (aunque el catálogo cambie después). Tesorería y totales de checkout intactos. Django Admin no dispara el sync: solo muestra el snapshot; el inline del pedido deja las columnas esenciales (el lápiz abre el detalle).

## Incremento 3 — Pago vs liquidación

El pago del cliente no mueve tesorería. La liquidación MP guarda bruto, comisión real y neto; el libro solo acredita el neto en la cuenta con rol `mp`. El webhook reutiliza el Payment del checkout (unique `mp_payment_id`) y `upsert_mp_settlement` es idempotente. No se pueden borrar movimientos confirmados.

## Incremento 4 — Resumen

Pantalla `/dashboard/finanzas/` con permiso `finance.view_finance`. KPIs de ventas netas, contribución, gastos (aún 0) y resultado operativo, más flujo de tesorería y ranking. Los filtros de período/canal se conservan al abrir las líneas de venta. El layout usa grafito y rojo de acento, no el header rojo del dashboard operativo.

## Incremento 5 — Inventario

`/dashboard/finanzas/inventario/` lista el stock real (`Product.stock`; con variantes es la suma). El potencial es una proyección: vender todo al precio publicado, IVA 19% si aplica, COGS del costo vigente. No crea ventas ni movimientos. Ver requiere `view_finance`; crear/editar stock y ficha (como Admin: precios, costos, variantes, imágenes) requiere `manage_catalog`. Ajustar stock no cambia el precio de catálogo.

## Incremento 6 — Ingresos y venta física

Ingresos muestra totales del período (neta, contribución, IVA) y el atajo **+ Venta física**. Esa venta crea un `Order` canal `pos`, cobra el precio publicado, descuenta stock y sincroniza líneas. No reescribe `Product.price`. No usa Mercado Pago ni mueve tesorería (el pago queda aprobado; la caja espera liquidación). Permiso `add_manual_sale`. El producto se busca por nombre/SKU, marca o categoría; se agrega a un ticket, no a un combo eterno.

## Incremento 7 — Financiamiento

Aporte y préstamo entran a una cuenta de tesorería y no se mezclan con ventas. El aporte no deja deuda. El préstamo deja saldo pendiente; pagarlo saca plata de la cuenta elegida. Permiso `manage_financing` para registrar; ver el historial alcanza con `view_finance`.

## Incremento 8 — Compras de mercadería

`/dashboard/finanzas/compras/` registra compras a proveedor: ticket con búsqueda por nombre/SKU/marca/categoría, no un select eterno. Paga tesorería (salida confirmada) y no crea ventas ni gastos operativos. Un flag suma stock (`Product` o variante); otro actualiza el costo vigente. El snapshot de ventas ya sincronizadas y `Product.price` no se tocan. IVA crédito se parte del bruto si es afecto. Mutar requiere `manage_purchases`; ver el historial alcanza con `view_finance`.

## Incremento 9 — Gastos operativos

`/dashboard/finanzas/gastos/` registra opex por categorías agrupadas en infraestructura, servicios, publicidad u otros. Las categorías se pueden crear desde la pantalla (y en Admin). El bruto sale de tesorería; el neto resta al resultado operativo. IVA crédito se guarda aparte. No es compra de mercadería ni venta. Mutar requiere `register_expense`; ver alcanza con `view_finance`.

## Incremento 10 — Envíos únicos y devoluciones

Una sola fila `OrderShipment` por pedido: cobrado al cliente (del pedido), costo real al courier y costo asumido prorrateado a las líneas. Si se paga el flete, hay un movimiento de tesorería idempotente. No es opex. Las devoluciones (`OrderRefund`) no borran ni reescriben la venta; el KPI del período resta el neto devuelto. Envíos: `register_expense`. Devoluciones: `add_manual_sale`.

## Incremento 11 — Saldos

`/dashboard/finanzas/saldos/` es de solo lectura (`view_finance`). Caja y bancos salen del libro (inicial + entradas − salidas); ventas y rentabilidad, de las líneas sincronizadas; impuestos, IVA débito de ventas menos crédito de compras y opex. No hay saldo editable ni modelo de período tributario. El IVA es control interno, no declaración SII. El Resumen enlaza caja, bancos e IVA a estas pestañas.

## Incremento 12 — Cierre operativo

El Resumen avisa cuentas en negativo, ventas sin costo, stock en cero, IVA estimado a pagar, liquidaciones pendientes y préstamos abiertos; cada alerta abre la pantalla donde se corrige. La evolución de ventas netas es una barra CSS (día/semana/mes, sin Chart.js). `manage.py backfill_finance_sales` sincroniza pedidos viejos sin mover tesorería ni pisar costos ya congelados. Las tablas de gastos, compras, financiamiento, envíos y devoluciones pasan a tarjetas en móvil.
