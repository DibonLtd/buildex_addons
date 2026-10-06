from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_blacklisted_credit_sale_invoice(self):
        for move in self:
            if not move.is_sale_document(include_receipts=False):
                continue

            partner = move.partner_id.commercial_partner_id
            if partner.is_blacklisted and move.invoice_payment_term_id and move.invoice_payment_term_id.is_credit_sale_term:
                raise UserError(partner._get_blacklist_credit_sale_message())

    def action_post(self):
        self._check_blacklisted_credit_sale_invoice()
        return super().action_post()
