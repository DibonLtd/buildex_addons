from odoo import fields, models

from odoo.addons.payment_with_bank_till import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('bank_till', 'Bank Paybill (Equity)')],
        ondelete={'bank_till': 'set default'},
    )

    def _compute_feature_support_fields(self):
        """Override of `payment` to configure supported features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'bank_till').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_refund': False,
            'support_tokenization': False,
        })

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'bank_till':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
