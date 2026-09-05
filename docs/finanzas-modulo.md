# Módulo Finanzas — bitácora breve de incrementos

## Incremento 1 — Cimientos

App `finance` con cuentas de tesorería (saldo derivado, no editable). El catálogo ganó SKU y costo vigente; el pedido, canal y estado financiero; cada `OrderItem` quedó listo para snapshots. El dinero se calcula con Decimal (CLP entero, IVA 19%, prorrateo que cierra al peso). Permisos `finance.view_finance` y afines; el storefront no cambió. Tests de IVA, prorrateo y saldo inicial.

## Incremento 2 — Sync de venta

Al crear un pedido web, `sync_sale_from_order` congela por línea SKU, precio lista, venta bruta/neta, IVA y costo histórico. El descuento del pedido se reparte proporcional al neto; el envío cobrado también, sin duplicar el monto. Re-ejecutar el sync no pisa el costo (aunque el catálogo cambie después). Tesorería y totales de checkout intactos. Django Admin no dispara el sync: solo muestra el snapshot; el inline del pedido deja las columnas esenciales (el lápiz abre el detalle).

## Incremento 3 — Pago vs liquidación

El pago del cliente no mueve tesorería. La liquidación MP guarda bruto, comisión real y neto; el libro solo acredita el neto en la cuenta con rol `mp`. El webhook reutiliza el Payment del checkout (unique `mp_payment_id`) y `upsert_mp_settlement` es idempotente. No se pueden borrar movimientos confirmados.

## Incremento 4 — Resumen

Pantalla `/dashboard/finanzas/` con permiso `finance.view_finance`. KPIs de ventas netas, contribución, gastos (aún 0) y resultado operativo, más flujo de tesorería y ranking. Los filtros de período/canal se conservan al abrir las líneas de venta. El layout usa grafito y rojo de acento, no el header rojo del dashboard operativo.
