from odoo import api, fields, models


class BuildexProject(models.Model):
    _name = 'buildex.project'
    _description = 'Buildex Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    def _buildex_default_ref(self, xmlid):
        record = self.env.ref(xmlid, raise_if_not_found=False)
        return record.id if record else False

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        string='Project ID',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True,
    )
    project_type_id = fields.Many2one(
        'buildex.project.type',
        string='Project Type',
        required=True,
        default=lambda self: self._buildex_default_ref('buildex_monitoring_dashboard.buildex_project_type_residential'),
        tracking=True,
    )
    residential_use_id = fields.Many2one(
        'buildex.residential.use',
        string='Residential Use',
    )
    stage_id = fields.Many2one(
        'buildex.project.stage',
        string='Stage',
        required=True,
        default=lambda self: self._buildex_default_ref('buildex_monitoring_dashboard.buildex_project_stage_planning'),
        tracking=True,
    )
    budget_range_id = fields.Many2one(
        'buildex.budget.range',
        string='Budget Range',
        tracking=True,
    )
    start_date = fields.Date(tracking=True)
    expected_completion_date = fields.Date(tracking=True)
    material_decision_maker_id = fields.Many2one(
        'buildex.decision.maker',
        string='Material Decision Maker',
        tracking=True,
    )
    fundi_id = fields.Many2one(
        'res.partner',
        string='Preferred Fundi',
        domain=[('is_fundi', '=', True)],
        tracking=True,
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)
    sale_order_ids = fields.One2many('sale.order', 'buildex_project_id', string='Sales Orders')
    feedback_ids = fields.One2many('buildex.feedback', 'project_id', string='Feedback')
    followup_ids = fields.One2many('buildex.followup', 'project_id', string='Follow-ups')
    assigned_user_id = fields.Many2one('res.users', string='Assigned Staff', tracking=True)
    next_expected_need_id = fields.Many2one(
        'buildex.next.need',
        compute='_compute_monitoring_metrics',
        store=True,
        string='Next Expected Need',
    )
    last_activity_date = fields.Date(
        compute='_compute_monitoring_metrics',
        store=True,
        string='Last Activity',
    )
    pending_followup_count = fields.Integer(
        compute='_compute_monitoring_metrics',
        store=True,
        string='Pending Follow-ups',
    )
    open_followup_ids = fields.Many2many(
        'buildex.followup',
        compute='_compute_monitoring_metrics',
        string='Open Follow-ups',
    )
    hot_lead = fields.Boolean(
        compute='_compute_monitoring_metrics',
        store=True,
        string='Hot Lead',
    )
    demand_signal = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        compute='_compute_monitoring_metrics',
        store=True,
        string='Demand Signal',
    )
    sale_order_count = fields.Integer(compute='_compute_counts')
    feedback_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('buildex_project_code_unique', 'unique(code)', 'Project ID must be unique.'),
    ]

    @api.depends('sale_order_ids', 'feedback_ids')
    def _compute_counts(self):
        for record in self:
            record.sale_order_count = len(record.sale_order_ids)
            record.feedback_count = len(record.feedback_ids)

    @api.depends(
        'stage_id',
        'project_type_id',
        'feedback_ids.feedback_date',
        'sale_order_ids.date_order',
        'sale_order_ids.state',
        'followup_ids.state',
        'followup_ids.due_date',
    )
    def _compute_monitoring_metrics(self):
        need_map = {
            'planning': 'buildex_monitoring_dashboard.buildex_next_need_quotation',
            'foundation': 'buildex_monitoring_dashboard.buildex_next_need_site_visit',
            'walling_structure': 'buildex_monitoring_dashboard.buildex_next_need_product_recommendation',
            'roofing': 'buildex_monitoring_dashboard.buildex_next_need_technical_advice',
            'doors_frame': 'buildex_monitoring_dashboard.buildex_next_need_product_recommendation',
            'walling_interior_finish': 'buildex_monitoring_dashboard.buildex_next_need_installation_support',
            'ceiling': 'buildex_monitoring_dashboard.buildex_next_need_installation_support',
            'flooring': 'buildex_monitoring_dashboard.buildex_next_need_product_recommendation',
            'cabinetry': 'buildex_monitoring_dashboard.buildex_next_need_product_recommendation',
            'paint_work': 'buildex_monitoring_dashboard.buildex_next_need_repeat_purchase',
            'gardening': 'buildex_monitoring_dashboard.buildex_next_need_repeat_purchase',
            'renovation': 'buildex_monitoring_dashboard.buildex_next_need_site_visit',
        }
        today = fields.Date.to_date(fields.Date.context_today(self))
        month_start = today.replace(day=1)
        for record in self:
            pending_followups = record.followup_ids.filtered(
                lambda followup: followup.state not in ('done', 'cancelled')
            )
            latest_dates = (
                record.feedback_ids.mapped('feedback_date')
                + record.sale_order_ids.mapped('date_order')
                + record.followup_ids.mapped('due_date')
            )
            latest_dates = [value.date() if hasattr(value, 'date') else value for value in latest_dates if value]
            record.last_activity_date = max(latest_dates) if latest_dates else False
            record.pending_followup_count = len(pending_followups)
            record.open_followup_ids = pending_followups
            xmlid = need_map.get(record.stage_id.code)
            record.next_expected_need_id = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False
            recent_order_count = len(record.sale_order_ids.filtered(
                lambda order: order.date_order and order.date_order.date() >= month_start
            ))
            record.hot_lead = record.stage_id.code in ('planning', 'foundation', 'walling_structure') and (
                recent_order_count > 0 or len(pending_followups) > 0
            )
            if recent_order_count >= 2 or record.stage_id.code in ('roofing', 'ceiling', 'paint_work'):
                record.demand_signal = 'high'
            elif recent_order_count == 1 or record.stage_id.code in ('foundation', 'walling_structure', 'flooring'):
                record.demand_signal = 'medium'
            else:
                record.demand_signal = 'low'

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = sequence.next_by_code('buildex.project') or 'New'
        return super().create(vals_list)

    def name_get(self):
        result = []
        for record in self:
            display = f'[{record.code}] {record.name}'
            result.append((record.id, display))
        return result
