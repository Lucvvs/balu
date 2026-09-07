from django.core.management.base import BaseCommand

from finance.services.backfill import backfill_unsynced_sales


class Command(BaseCommand):
    help = (
        'Sincroniza el snapshot financiero de pedidos que aún no lo tienen. '
        'No mueve tesorería ni pisa costos ya congelados.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Cuenta pedidos pendientes sin escribir.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Máximo de pedidos a sincronizar (0 = todos).',
        )

    def handle(self, *args, **options):
        result = backfill_unsynced_sales(
            dry_run=options['dry_run'],
            limit=options['limit'] or None,
        )
        found = result['found']
        if result['dry_run']:
            self.stdout.write(f'{found} pedido(s) pendientes de snapshot. Sin cambios (dry-run).')
            return
        self.stdout.write(self.style.SUCCESS(
            f'Sincronizados {result["synced"]} de {found} pedido(s). Tesorería intacta.'
        ))
