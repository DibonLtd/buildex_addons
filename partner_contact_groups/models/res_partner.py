from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_group_ids = fields.Many2many(
        'partner.contact.group',
        'res_partner_contact_group_rel',
        'partner_id',
        'group_id',
        string='Contact Groups',
    )
