from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """After delivery is validated, immediately recompute influencer stage on linked sale orders."""
        res = super()._action_done()
        sale_orders = self.mapped('sale_id').filtered(lambda o: o.id)
        if sale_orders:
            sale_orders.sudo()._compute_influencer_order_stage()
        return res
