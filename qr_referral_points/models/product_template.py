from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    influencer_commission_rate = fields.Float(
        string="Influencer Commission Rate (%)",
        help=(
            "If set, this rate takes priority over the commission plan category rate. "
            "If empty, the system falls back to the commission plan category rule, then the plan default rate."
        ),
    )
