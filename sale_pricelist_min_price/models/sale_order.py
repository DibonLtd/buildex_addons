from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_minimum_pricelist_prices(self):
        self.mapped('order_line')._check_minimum_pricelist_price()

    def write(self, vals):
        result = super().write(vals)
        if 'pricelist_id' in vals:
            self._check_minimum_pricelist_prices()
        return result

    def action_confirm(self):
        self._check_minimum_pricelist_prices()
        return super().action_confirm()
