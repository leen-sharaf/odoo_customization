from odoo import models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):

        errors = []

        for picking in self:

            if picking.picking_type_id.code == 'incoming':
                continue

            if picking.location_id.usage == 'inventory':
                continue

            for move in picking.move_ids:
                if not move.location_id or not move.product_id:
                    continue

                if not move.quantity:
                    continue

                if not move.product_id.tracking:
                    continue

                grouped = self.env['stock.quant'].read_group(
                    domain=[
                        ('location_id', 'child_of', move.location_id.id),
                        ('product_id', '=', move.product_id.id),
                    ],
                    fields=[
                        'available_quantity:sum',
                        'inventory_quantity_auto_apply:sum',
                        'reserved_quantity:sum',
                        'quantity:sum',
                    ],
                    groupby=['product_id'],
                )

                available_qty = grouped[0]['available_quantity'] if grouped else 0.0
                inventoried_qty = grouped[0]['inventory_quantity_auto_apply'] if grouped else 0.0
                reserved_qty = grouped[0]['reserved_quantity'] if grouped else 0.0
                qty = grouped[0]['quantity'] if grouped else 0.0

                _logger.info("Inventoried quantity: %s", inventoried_qty)

                if not available_qty and not qty:
                    if available_qty - move.quantity <= 0:
                        errors.append(_(
                            "Location: %s | Product: %s → No available quantity in this location."
                        ) % (
                                        move.location_id.display_name,
                                        move.product_id.display_name,
                                    ))
                        continue


                _logger.info("Available quantity: %s", available_qty)
                if picking.state in ('confirmed','assigned'):
                    condition_failed = (available_qty + move.quantity) < move.quantity
                else:
                    condition_failed = False

                if condition_failed:
                    errors.append(_(
                        "Location: %s | Product: %s | Available Quantity: %.2f | Requested Quantity: %.2f | On Hand Quantity: %.2f| Reserved Quantity: %.2f"
                    ) % (
                        move.location_id.display_name,
                        move.product_id.display_name,
                        available_qty,
                        move.quantity,
                        inventoried_qty,
                        reserved_qty,
                    ))

        # raise ONE error with all problems
        if errors:
            raise ValidationError(
                _("Stock not sufficient for the following lines:\n\n%s")
                % "\n".join(errors)
            )

        return super().button_validate()
#push me here
#leen