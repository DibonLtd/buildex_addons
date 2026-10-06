from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    ask_payment_reference = fields.Boolean(
        string="Ask for Payment Reference",
        help="Prompt the cashier for a payment reference when this method is selected in POS.",
    )
    payment_reference_required = fields.Boolean(
        string="Reference is Required",
        help="Block creating the POS payment line until a payment reference is entered.",
    )
    payment_reference_label = fields.Char(
        string="Reference Label",
        default="Payment Reference",
        help="Label shown to the cashier in the POS popup.",
    )

    def _load_pos_data_fields(self, config_id):
        fields_to_load = list(super()._load_pos_data_fields(config_id))
        fields_to_load.extend(
            [
                "ask_payment_reference",
                "payment_reference_required",
                "payment_reference_label",
            ]
        )
        return fields_to_load
