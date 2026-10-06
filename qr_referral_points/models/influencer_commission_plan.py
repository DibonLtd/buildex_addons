from odoo import models, fields, api


class InfluencerCommissionPlan(models.Model):
    _name = 'influencer.commission.plan'
    _description = 'Influencer Commission Plan'

    FIXED_WITHHOLDING_TAX_RATE = 5.0

    name = fields.Char(required=True)
    default_rate = fields.Float(required=True, help="Commission rate applied to sale value (e.g. 5 = 5%)")

    topline_bonus_rate = fields.Float(
        string="Topline Bonus Rate (%)",
        default=10.0,
        help="Percentage of influencer commission paid to the topline mentor (e.g. 10 = 10%, 15 = 15%)",
    )

    withholding_tax_rate = fields.Float(
        string="Withholding Tax Rate (%)",
        default=FIXED_WITHHOLDING_TAX_RATE,
        help="Withholding tax deducted from net earnings and shown on the payout bill",
    )

    @api.model
    def _get_withholding_tax_rate(self):
        return self.FIXED_WITHHOLDING_TAX_RATE

    rule_ids = fields.One2many(
        'influencer.commission.rule',
        'plan_id'
    )

    auto_payout_enabled = fields.Boolean(
        string="Enable Auto Payout",
        default=False
    )

    auto_payout_minimum = fields.Monetary(
        string="Minimum Wallet Amount for Auto Payout"
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    active = fields.Boolean(default=True)

    def _get_rate_for_product(self, product):
        self.ensure_one()
        if not product:
            return self.default_rate

        template = product.product_tmpl_id
        if template and template.influencer_commission_rate not in (False, None):
            return template.influencer_commission_rate

        rule = self.rule_ids.filtered(lambda r: r.categ_id == product.categ_id)[:1]
        return rule.rate if rule else self.default_rate
