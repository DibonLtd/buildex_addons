from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class BuildexFundiRequest(models.Model):
    _name = 'buildex.fundi.request'
    _description = 'Buildex Fundi Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_datetime desc, id desc'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    active = fields.Boolean(default=True)
    request_date = fields.Date(
        default=lambda self: fields.Date.context_today(self),
        required=True,
        tracking=True,
        index=True,
    )
    request_datetime = fields.Datetime(
        default=lambda self: fields.Datetime.now(),
        required=True,
        tracking=True,
        index=True,
    )
    source = fields.Selection(
        [
            ('website_form', 'Website Form'),
            ('checkout_post_payment', 'Checkout Post Payment'),
            ('contact_sales_form', 'Contact Sales Form'),
            ('manual', 'Manual Entry'),
        ],
        required=True,
        default='manual',
        tracking=True,
    )
    request_type = fields.Selection(
        [
            ('fundi_support', 'Fundi Support'),
            ('sales_inquiry', 'Sales Inquiry'),
        ],
        required=True,
        default='fundi_support',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True,
        index=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        tracking=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        tracking=True,
        index=True,
    )
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
        index=True,
    )
    assigned_fundi_id = fields.Many2one(
        'res.partner',
        string='Assigned Fundi',
        domain=[('is_fundi', '=', True)],
        tracking=True,
        index=True,
    )
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent')],
        default='2',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('new', 'New'),
            ('pending_response', 'Pending Response'),
            ('contacted', 'Contacted'),
            ('assigned', 'Assigned Fundi'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='new',
        required=True,
        tracking=True,
    )
    requested_by_name = fields.Char(string='Requested By', tracking=True)
    phone = fields.Char(tracking=True)
    email = fields.Char(tracking=True)
    city = fields.Char(string='Town / Location', tracking=True)
    requested_service = fields.Char(
        string='Requested Service',
        default='Fundi / Technician Support',
        tracking=True,
    )
    action_point = fields.Selection(
        [
            ('call_customer', 'Call Customer'),
            ('confirm_location', 'Confirm Location'),
            ('assign_nearest_fundi', 'Assign Nearest Fundi'),
            ('sales_callback', 'Sales Callback'),
            ('prepare_quote', 'Prepare Quote'),
            ('follow_up', 'Follow Up'),
            ('waiting_customer', 'Waiting for Customer'),
        ],
        default='call_customer',
        required=True,
        tracking=True,
    )
    note = fields.Text(string='Customer Request / Notes')
    internal_note = fields.Text(string='Internal Action Notes')
    response_deadline = fields.Datetime(
        required=True,
        tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=4),
    )
    first_response_date = fields.Datetime(string='First Response On', tracking=True)
    completion_date = fields.Datetime(readonly=True, tracking=True)
    response_done = fields.Boolean(compute='_compute_attention_metrics', string='Responded')
    is_overdue = fields.Boolean(compute='_compute_attention_metrics', search='_search_is_overdue')
    needs_attention = fields.Boolean(compute='_compute_attention_metrics')
    age_in_days = fields.Integer(compute='_compute_attention_metrics', string='Age (Days)')
    alert_level = fields.Selection(
        [('normal', 'Normal'), ('warning', 'Warning'), ('critical', 'Critical')],
        compute='_compute_attention_metrics',
        string='Alert Level',
    )
    followup_count = fields.Integer(compute='_compute_followup_count', string='Follow-up Count')
    followup_ids = fields.One2many('buildex.followup', 'fundi_request_id', string='Follow-ups')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends('followup_ids')
    def _compute_followup_count(self):
        for record in self:
            record.followup_count = len(record.followup_ids)

    @api.depends('request_datetime', 'response_deadline', 'state', 'first_response_date')
    def _compute_attention_metrics(self):
        now = fields.Datetime.now()
        for record in self:
            record.response_done = bool(
                record.first_response_date or record.state in ('contacted', 'assigned', 'completed')
            )
            record.is_overdue = bool(
                record.response_deadline
                and record.state not in ('completed', 'cancelled')
                and not record.response_done
                and record.response_deadline < now
            )
            record.needs_attention = bool(
                record.state not in ('completed', 'cancelled')
                and (record.is_overdue or not record.response_done)
            )
            if record.request_datetime:
                delta = now - record.request_datetime
                record.age_in_days = max(delta.days, 0)
            else:
                record.age_in_days = 0
            if record.is_overdue:
                record.alert_level = 'critical'
            elif record.state in ('new', 'pending_response') and not record.response_done:
                record.alert_level = 'warning'
            else:
                record.alert_level = 'normal'

    def _search_is_overdue(self, operator, value):
        now = fields.Datetime.now()
        overdue_domain = [
            ('response_deadline', '<', now),
            ('state', 'not in', ('completed', 'cancelled')),
            ('first_response_date', '=', False),
        ]
        if operator in ('=', '==') and value:
            return overdue_domain
        return [('id', 'not in', self.search(overdue_domain).ids)]

    def _set_first_response_if_missing(self):
        pending = self.filtered(lambda record: not record.first_response_date)
        if pending:
            pending.write({'first_response_date': fields.Datetime.now()})

    def action_start_response(self):
        self.write({'state': 'pending_response'})

    def action_mark_contacted(self):
        self._set_first_response_if_missing()
        self.write({'state': 'contacted'})

    def action_assign_fundi(self):
        for record in self:
            if not record.assigned_fundi_id:
                raise UserError('Select a fundi before assigning the request.')
        self._set_first_response_if_missing()
        self.write({'state': 'assigned'})

    def action_mark_completed(self):
        self._set_first_response_if_missing()
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_new(self):
        self.write({
            'state': 'new',
            'completion_date': False,
        })

    def action_create_followup(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError('A customer must be linked before creating a follow-up.')

        followup = self.env['buildex.followup'].create({
            'name': f'Fundi request follow-up {self.name}',
            'partner_id': self.partner_id.id,
            'sale_order_id': self.sale_order_id.id,
            'assigned_user_id': self.assigned_user_id.id or self.env.user.id,
            'due_date': fields.Date.context_today(self),
            'note': self.note or self.internal_note,
            'fundi_request_id': self.id,
        })
        action = self.env.ref('buildex_monitoring_dashboard.action_buildex_followups').read()[0]
        action['res_id'] = followup.id
        action['views'] = [(False, 'form')]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('buildex.fundi.request') or 'New'
            request_datetime = vals.get('request_datetime')
            if request_datetime and not vals.get('request_date'):
                vals['request_date'] = fields.Datetime.to_datetime(request_datetime).date()
            if not vals.get('response_deadline'):
                base_dt = (
                    fields.Datetime.to_datetime(request_datetime)
                    if request_datetime
                    else fields.Datetime.now()
                )
                vals['response_deadline'] = base_dt + timedelta(hours=4)
        return super().create(vals_list)
