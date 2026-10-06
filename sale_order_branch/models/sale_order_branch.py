from odoo import api, fields, models


class SaleOrderBranch(models.Model):
    _name = 'sale.order.branch'
    _description = 'Sales Order Branch'
    _order = 'name, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Branch Contact',
        domain="[('is_company', '=', True)]",
        help='Optional company contact representing this branch.',
    )
    sale_order_ids = fields.One2many('sale.order', 'branch_id', string='Sales Orders')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count')

    _sql_constraints = [
        ('sale_order_branch_name_company_uniq', 'unique(name, company_id)', 'The branch name must be unique per company.'),
        ('sale_order_branch_partner_uniq', 'unique(partner_id)', 'A contact can only be linked to one branch.'),
    ]

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for branch in self:
            branch.sale_order_count = len(branch.sale_order_ids)

