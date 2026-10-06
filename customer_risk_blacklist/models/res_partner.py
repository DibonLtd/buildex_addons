from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bounced_cheque_ids = fields.One2many(
        'customer.bounced.cheque',
        'partner_id',
        string='Bounced Cheques',
    )
    bounced_cheque_count = fields.Integer(
        compute='_compute_risk_profile',
        string='Bounced Cheques',
    )
    bounced_cheque_blacklist_limit = fields.Integer(
        compute='_compute_risk_profile',
        string='Blacklist Limit',
    )
    risk_status = fields.Selection(
        [
            ('clear', 'Clear'),
            ('warning', 'Warning'),
            ('blacklisted', 'Blacklisted'),
        ],
        compute='_compute_risk_profile',
        string='Risk Status',
    )
    is_blacklisted = fields.Boolean(
        compute='_compute_risk_profile',
        string='Blacklisted',
    )

    @api.model
    def _get_bounced_cheque_blacklist_limit(self):
        limit = self.env['ir.config_parameter'].sudo().get_param(
            'customer_risk_blacklist.bounced_cheque_limit',
            default='3',
        )
        try:
            return max(int(limit), 0)
        except (TypeError, ValueError):
            return 3

    @api.depends('commercial_partner_id', 'commercial_partner_id.bounced_cheque_ids')
    def _compute_risk_profile(self):
        commercial_partners = self.mapped('commercial_partner_id')
        grouped_data = self.env['customer.bounced.cheque'].read_group(
            [('partner_id', 'in', commercial_partners.ids)],
            ['partner_id'],
            ['partner_id'],
        )
        count_by_partner = {
            group['partner_id'][0]: group['partner_id_count']
            for group in grouped_data
            if group.get('partner_id')
        }
        blacklist_limit = self._get_bounced_cheque_blacklist_limit()

        for partner in self:
            commercial_partner = partner.commercial_partner_id
            bounced_cheque_count = count_by_partner.get(commercial_partner.id, 0)
            is_blacklisted = bool(blacklist_limit and bounced_cheque_count > blacklist_limit)

            partner.bounced_cheque_count = bounced_cheque_count
            partner.bounced_cheque_blacklist_limit = blacklist_limit
            partner.is_blacklisted = is_blacklisted
            if is_blacklisted:
                partner.risk_status = 'blacklisted'
            elif bounced_cheque_count:
                partner.risk_status = 'warning'
            else:
                partner.risk_status = 'clear'

    def action_view_bounced_cheques(self):
        self.ensure_one()
        action = self.env.ref('customer_risk_blacklist.action_customer_bounced_cheque').read()[0]
        commercial_partner = self.commercial_partner_id
        action['domain'] = [('partner_id', '=', commercial_partner.id)]
        action['context'] = {
            'default_partner_id': commercial_partner.id,
            'search_default_partner_id': commercial_partner.id,
        }
        return action

    def _get_blacklist_credit_sale_message(self):
        self.ensure_one()
        return _(
            '%(customer)s is blacklisted for credit sales because %(count)s bounced cheques exceed the limit of %(limit)s.',
            customer=self.display_name,
            count=self.bounced_cheque_count,
            limit=self.bounced_cheque_blacklist_limit,
        )
