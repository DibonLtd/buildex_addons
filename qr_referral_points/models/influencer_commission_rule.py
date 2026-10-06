from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InfluencerCommissionRule(models.Model):
    _name = 'influencer.commission.rule'
    _description = 'Commission Rule Per Category'

    plan_id = fields.Many2one(
        'influencer.commission.plan',
        required=True,
        ondelete='cascade'
    )

    categ_id = fields.Many2one(
        'product.category',
        required=True
    )

    rate = fields.Float(required=True)

    