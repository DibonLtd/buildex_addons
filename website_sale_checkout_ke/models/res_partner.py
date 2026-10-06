from odoo import Command, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    checkout_payment_policy = fields.Selection(
        [
            ('confirm_only', 'Order First (No Payment)'),
            ('enforce_payment', 'Require Online Payment'),
        ],
        string='Website Checkout Payment Policy',
        default='enforce_payment',
    )

    is_fundi = fields.Boolean(
        string='Is Fundi',
        help='Mark this contact as a Fundi (installation technician).',
        default=False,
    )

    def _get_fundi_category(self):
        return self.env.ref('website_sale_checkout_ke.partner_category_fundi', raise_if_not_found=False)

    def _sync_fundi_category_from_flag(self):
        fundi_category = self._get_fundi_category()
        if not fundi_category or self.env.context.get('skip_fundi_group_sync'):
            return

        for partner in self:
            has_fundi_tag = fundi_category in partner.category_id
            if partner.is_fundi and not has_fundi_tag:
                partner.with_context(skip_fundi_group_sync=True).write({
                    'category_id': [Command.link(fundi_category.id)],
                })
            elif not partner.is_fundi and has_fundi_tag:
                partner.with_context(skip_fundi_group_sync=True).write({
                    'category_id': [Command.unlink(fundi_category.id)],
                })

    def _sync_fundi_flag_from_category(self):
        fundi_category = self._get_fundi_category()
        if not fundi_category or self.env.context.get('skip_fundi_group_sync'):
            return

        for partner in self:
            has_fundi_tag = fundi_category in partner.category_id
            if partner.is_fundi != has_fundi_tag:
                partner.with_context(skip_fundi_group_sync=True).write({
                    'is_fundi': has_fundi_tag,
                })

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._sync_fundi_flag_from_category()
        partners._sync_fundi_category_from_flag()
        return partners

    def write(self, vals):
        result = super().write(vals)
        if 'is_fundi' in vals:
            self._sync_fundi_category_from_flag()
        if 'category_id' in vals:
            self._sync_fundi_flag_from_category()
        return result
