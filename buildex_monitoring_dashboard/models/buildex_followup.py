from odoo import api, fields, models


class BuildexFollowup(models.Model):
    _name = 'buildex.followup'
    _description = 'Buildex Follow-up'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, due_date asc, id desc'

    def _buildex_default_ref(self, xmlid):
        record = self.env.ref(xmlid, raise_if_not_found=False)
        return record.id if record else False

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent')],
        default='1',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='scheduled',
        required=True,
        tracking=True,
    )
    due_date = fields.Date(required=True, tracking=True, index=True)
    reminder_date = fields.Date(tracking=True)
    completion_date = fields.Date(readonly=True, tracking=True)
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, index=True)
    project_id = fields.Many2one('buildex.project', string='Project', tracking=True, index=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', tracking=True, index=True)
    feedback_id = fields.Many2one('buildex.feedback', string='Feedback', tracking=True, index=True)
    fundi_request_id = fields.Many2one(
        'buildex.fundi.request',
        string='Fundi Request',
        tracking=True,
        index=True,
    )
    next_expected_need_id = fields.Many2one(
        'buildex.next.need',
        tracking=True,
        string='Next Expected Need',
    )
    buildex_activity_type_id = fields.Many2one(
        'buildex.followup.activity.type',
        string='Buildex Activity Type',
        default=lambda self: self._buildex_default_ref('buildex_monitoring_dashboard.buildex_followup_activity_call'),
        required=True,
        tracking=True,
    )
    note = fields.Text(string='Notes')
    last_activity_date = fields.Date(
        compute='_compute_last_activity_date',
        string='Related Last Activity',
    )
    is_overdue = fields.Boolean(compute='_compute_is_overdue', search='_search_is_overdue')

    @api.depends('partner_id.buildex_last_activity_date', 'project_id.last_activity_date')
    def _compute_last_activity_date(self):
        for record in self:
            record.last_activity_date = record.project_id.last_activity_date or record.partner_id.buildex_last_activity_date

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.due_date
                and record.state not in ('done', 'cancelled')
                and record.due_date < today
            )

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        overdue_domain = [
            ('due_date', '<', today),
            ('state', 'not in', ('done', 'cancelled')),
        ]
        if operator in ('=', '==') and value:
            return overdue_domain
        return [('id', 'not in', self.search(overdue_domain).ids)]

    def action_mark_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_mark_done(self):
        self.write({
            'state': 'done',
            'completion_date': fields.Date.context_today(self),
        })

    def action_reset_to_scheduled(self):
        self.write({
            'state': 'scheduled',
            'completion_date': False,
        })
