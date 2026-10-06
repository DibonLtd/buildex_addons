from odoo import fields, models


class PartnerContactGroup(models.Model):
    _name = 'partner.contact.group'
    _description = 'Partner Contact Group'
    _order = 'sequence, name, id'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color Index')
    partner_ids = fields.Many2many(
        'res.partner',
        'res_partner_contact_group_rel',
        'group_id',
        'partner_id',
        string='Partners',
    )

    _sql_constraints = [
        ('partner_contact_group_name_uniq', 'unique(name)', 'The contact group name must be unique.'),
    ]
