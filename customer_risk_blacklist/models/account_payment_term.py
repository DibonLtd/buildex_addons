from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    is_credit_sale_term = fields.Boolean(
        compute='_compute_is_credit_sale_term',
        string='Is Credit Sale Term',
    )

    @api.depends('line_ids.value', 'line_ids.value_amount', 'line_ids.delay_type', 'line_ids.nb_days')
    def _compute_is_credit_sale_term(self):
        for payment_term in self:
            payment_term.is_credit_sale_term = not payment_term._is_immediate_payment_term()

    def _is_immediate_payment_term(self):
        self.ensure_one()
        if len(self.line_ids) != 1:
            return False

        line = self.line_ids[0]
        return (
            line.value == 'percent'
            and float_compare(line.value_amount, 100.0, precision_digits=2) == 0
            and line.delay_type == 'days_after'
            and line.nb_days == 0
        )
