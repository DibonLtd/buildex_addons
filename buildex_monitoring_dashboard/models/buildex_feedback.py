from odoo import api, fields, models


class BuildexFeedback(models.Model):
    _name = 'buildex.feedback'
    _description = 'Buildex Feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'feedback_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
    feedback_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, index=True)
    project_id = fields.Many2one('buildex.project', string='Project', tracking=True, index=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', tracking=True)
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        domain="[('move_type', '=', 'out_invoice')]",
        tracking=True,
    )
    fundi_id = fields.Many2one(
        'res.partner',
        string='Fundi / Installer',
        domain=[('is_fundi', '=', True)],
        tracking=True,
    )
    product_satisfaction = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='Product Satisfaction',
        tracking=True,
    )
    fundi_satisfaction = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='Was the Fundi Satisfactory?',
        tracking=True,
    )
    would_recommend_buildex = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Would Recommend Buildex?',
        tracking=True,
    )
    additional_need = fields.Text(string='What Else Do You Need?')
    notes = fields.Text(string='Internal Notes')
    followup_required = fields.Boolean(string='Needs Follow-up', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('buildex.feedback') or 'New'
        records = super().create(vals_list)
        records._create_followups_from_feedback()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'followup_required' in vals:
            self._create_followups_from_feedback()
        return result

    def _create_followups_from_feedback(self):
        followup_model = self.env['buildex.followup']
        support_activity = self.env.ref(
            'buildex_monitoring_dashboard.buildex_followup_activity_support',
            raise_if_not_found=False,
        )
        feedback_need = self.env.ref(
            'buildex_monitoring_dashboard.buildex_next_need_feedback_collection',
            raise_if_not_found=False,
        )
        for record in self:
            if not record.followup_required:
                continue
            existing_followup = followup_model.search([
                ('feedback_id', '=', record.id),
                ('state', 'not in', ('done', 'cancelled')),
            ], limit=1)
            if existing_followup:
                continue
            followup_model.create({
                'name': f'Feedback Follow-up: {record.name}',
                'partner_id': record.partner_id.id,
                'project_id': record.project_id.id,
                'sale_order_id': record.sale_order_id.id,
                'feedback_id': record.id,
                'assigned_user_id': self.env.user.id,
                'due_date': fields.Date.context_today(self),
                'priority': '2',
                'buildex_activity_type_id': support_activity.id if support_activity else False,
                'next_expected_need_id': feedback_need.id if feedback_need else False,
                'note': record.additional_need or record.notes,
            })
