from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_pricelist_minimum_unit_price(self):
        self.ensure_one()
        order = self.order_id
        quantity = self.product_uom_qty or 1.0
        return order.pricelist_id._get_product_price(
            product=self.product_id,
            quantity=quantity,
            currency=order.currency_id,
            uom=self.product_uom,
            date=order.date_order,
        )

    def _check_minimum_pricelist_price(self):
        for line in self:
            order = line.order_id
            if not order or order.state not in ('draft', 'sent'):
                continue
            if line.display_type or line.is_downpayment or not line.product_id or not order.pricelist_id:
                continue

            minimum_price = line._get_pricelist_minimum_unit_price()
            if float_compare(
                line.price_unit,
                minimum_price,
                precision_rounding=order.currency_id.rounding,
            ) < 0:
                raise UserError(_(
                    'The unit price for "%(product)s" cannot be lower than the pricelist price.\n'
                    'Minimum allowed: %(minimum).2f\n'
                    'Entered price: %(entered).2f'
                ) % {
                    'product': line.product_id.display_name,
                    'minimum': minimum_price,
                    'entered': line.price_unit,
                })

    @api.constrains('price_unit', 'product_id', 'product_uom_qty', 'product_uom', 'order_id')
    def _constrain_minimum_pricelist_price(self):
        self._check_minimum_pricelist_price()

    def write(self, vals):
        result = super().write(vals)
        self._check_minimum_pricelist_price()
        return result
