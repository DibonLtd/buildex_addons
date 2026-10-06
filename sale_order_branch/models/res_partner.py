from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_branch_id = fields.Many2one(
        'sale.order.branch',
        string='Sales Branch',
        readonly=True,
        copy=False,
    )

    def _is_branch_contact_candidate(self):
        self.ensure_one()
        return bool(self.parent_id and self.is_company)

    def _prepare_sale_branch_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'company_id': self.company_id.id or self.env.company.id,
            'partner_id': self.id,
            'active': self.active,
        }

    def _sync_sale_branch(self):
        branch_model = self.env['sale.order.branch'].sudo()
        for partner in self:
            if partner._is_branch_contact_candidate():
                vals = partner._prepare_sale_branch_vals()
                if partner.sale_branch_id:
                    partner.sale_branch_id.sudo().write(vals)
                else:
                    branch = branch_model.search([('partner_id', '=', partner.id)], limit=1)
                    if branch:
                        branch.write(vals)
                    else:
                        branch = branch_model.create(vals)
                    partner.sudo().sale_branch_id = branch.id
            elif partner.sale_branch_id:
                partner.sale_branch_id.sudo().write({
                    'partner_id': False,
                    'active': partner.active,
                })
                partner.sudo().sale_branch_id = False

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._sync_sale_branch()
        return partners

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {'name', 'parent_id', 'company_id', 'is_company', 'active'}
        if tracked_fields.intersection(vals):
            self._sync_sale_branch()
        return result
