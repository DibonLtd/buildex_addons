from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    branch_id = fields.Many2one(
        'sale.order.branch',
        string='Branch',
        required=True,
        help='Select the branch that originated or is handling this quotation or sales order.',
    )

    def action_request_from_main(self):
        main_company = self.env['res.company'].browse(1).exists()
        if not main_company:
            raise UserError(_('Main company with ID 1 was not found.'))

        for order in self:
            order.company_id = main_company.id
        return True
