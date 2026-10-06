from odoo import _, api, fields, models


class CustomerBouncedCheque(models.Model):
    _name = 'customer.bounced.cheque'
    _description = 'Customer Bounced Cheque'
    _order = 'incident_date desc, id desc'

    name = fields.Char(required=True, default=lambda self: _('Bounced Cheque'))
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    incident_date = fields.Date(
        string='Incident Date',
        required=True,
        default=fields.Date.context_today,
    )
    cheque_number = fields.Char()
    amount = fields.Monetary(currency_field='currency_id')
    note = fields.Text()
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id'):
                vals['partner_id'] = self.env['res.partner'].browse(vals['partner_id']).commercial_partner_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('partner_id'):
            vals['partner_id'] = self.env['res.partner'].browse(vals['partner_id']).commercial_partner_id.id
        return super().write(vals)
