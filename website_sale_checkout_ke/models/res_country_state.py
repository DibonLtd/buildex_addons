from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    is_delivery_town = fields.Boolean(
        string='Available for Website Delivery',
        default=True,
    )
