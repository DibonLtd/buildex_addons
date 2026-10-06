from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_pos_pricelist_for_partner(self, config, partner):
        default_pricelist = config.pricelist_id
        partner_pricelist = partner.property_product_pricelist

        if not partner_pricelist or not config:
            return default_pricelist

        return partner_pricelist

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super()._onchange_partner_id()
        for order in self:
            order.pricelist_id = order._get_pos_pricelist_for_partner(
                order.config_id,
                order.partner_id,
            )
