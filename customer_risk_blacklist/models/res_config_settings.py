from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bounced_cheque_blacklist_limit = fields.Integer(
        string='Bounced Cheque Blacklist Limit',
        config_parameter='customer_risk_blacklist.bounced_cheque_limit',
        default=3,
        help='Once a customer exceeds this number of bounced cheques, the customer is blacklisted for credit sales.',
    )

    @api.constrains('bounced_cheque_blacklist_limit')
    def _check_bounced_cheque_blacklist_limit(self):
        for settings in self:
            if settings.bounced_cheque_blacklist_limit < 0:
                raise ValidationError(_('The bounced cheque blacklist limit must be zero or greater.'))
