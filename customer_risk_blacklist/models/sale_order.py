from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _is_credit_sale_order(self):
        self.ensure_one()
        return bool(self.payment_term_id and self.payment_term_id.is_credit_sale_term)

    def _check_blacklisted_credit_sale(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if partner.is_blacklisted and order._is_credit_sale_order():
                raise UserError(partner._get_blacklist_credit_sale_message())

    @api.onchange('partner_id', 'payment_term_id')
    def _onchange_blacklisted_credit_sale(self):
        if self.partner_id.commercial_partner_id.is_blacklisted and self._is_credit_sale_order():
            return {
                'warning': {
                    'title': _('Blacklisted Customer'),
                    'message': self.partner_id.commercial_partner_id._get_blacklist_credit_sale_message(),
                }
            }
        return {}

    def action_confirm(self):
        self._check_blacklisted_credit_sale()
        return super().action_confirm()
