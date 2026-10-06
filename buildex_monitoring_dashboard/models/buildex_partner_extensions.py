from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _buildex_default_ref(self, xmlid):
        record = self.env.ref(xmlid, raise_if_not_found=False)
        return record.id if record else False

    buildex_alternative_phone = fields.Char(string='Alternative Phone')
    buildex_age_bracket_id = fields.Many2one(
        'buildex.age.bracket',
        string='Age Bracket',
        tracking=True,
    )
    buildex_customer_type_ids = fields.Many2many(
        'buildex.customer.type',
        'buildex_partner_customer_type_rel',
        'partner_id',
        'customer_type_id',
        string='Buildex Customer Types',
    )
    buildex_town = fields.Char(string='Buildex Town')
    buildex_area = fields.Char(string='Estate / Area')
    buildex_gps_pin = fields.Char(string='GPS Pin')
    buildex_acquisition_source_id = fields.Many2one(
        'buildex.acquisition.source',
        string='Acquisition Source',
        tracking=True,
    )
    buildex_influencer_partner_id = fields.Many2one(
        'res.partner',
        string='Influencer',
        domain=[('is_referrer', '=', True)],
    )
    buildex_acquisition_notes = fields.Text(string='Acquisition Notes')
    buildex_project_ids = fields.One2many('buildex.project', 'partner_id', string='Buildex Projects')
    buildex_feedback_ids = fields.One2many('buildex.feedback', 'partner_id', string='Buildex Feedback')
    buildex_followup_ids = fields.One2many('buildex.followup', 'partner_id', string='Buildex Follow-ups')
    buildex_fundi_request_ids = fields.One2many(
        'buildex.fundi.request',
        'partner_id',
        string='Fundi Requests',
    )
    buildex_assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned Staff',
        tracking=True,
    )
    buildex_next_expected_need_id = fields.Many2one(
        'buildex.next.need',
        string='Next Expected Need',
        tracking=True,
        default=lambda self: self._buildex_default_ref('buildex_monitoring_dashboard.buildex_next_need_quotation'),
    )
    buildex_last_activity_date = fields.Date(
        compute='_compute_buildex_customer_metrics',
        string='Last Activity',
        store=True,
    )
    buildex_pending_followup_count = fields.Integer(
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='Pending Follow-ups',
    )
    buildex_customer_health_segment = fields.Selection(
        [
            ('excellent', 'Excellent'),
            ('healthy', 'Healthy'),
            ('monitor', 'Monitor'),
            ('at_risk', 'At Risk'),
        ],
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='Health Segment',
    )
    buildex_customer_health_score = fields.Integer(
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='Health Score',
    )
    buildex_at_risk = fields.Boolean(
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='At Risk',
    )
    buildex_high_value_customer = fields.Boolean(
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='High Value Customer',
    )
    buildex_one_time_buyer = fields.Boolean(
        compute='_compute_buildex_customer_metrics',
        store=True,
        string='One-time Buyer',
    )
    buildex_total_sales_amount = fields.Monetary(
        compute='_compute_buildex_customer_metrics',
        string='Total Sales Amount',
        currency_field='currency_id',
        store=True,
    )
    buildex_influencer_quality_score = fields.Integer(
        compute='_compute_buildex_influencer_metrics',
        string='Influencer Quality Score',
    )
    buildex_influencer_rank = fields.Selection(
        [
            ('bronze', 'Bronze'),
            ('silver', 'Silver'),
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
        ],
        compute='_compute_buildex_influencer_metrics',
        string='Influencer Rank',
    )
    buildex_referral_sale_count = fields.Integer(
        compute='_compute_buildex_influencer_metrics',
        string='Referral Sales',
    )
    buildex_referral_revenue = fields.Monetary(
        compute='_compute_buildex_influencer_metrics',
        string='Referral Revenue',
        currency_field='currency_id',
    )

    buildex_skill_type_ids = fields.Many2many(
        'buildex.skill.type',
        'buildex_partner_skill_type_rel',
        'partner_id',
        'skill_type_id',
        string='Skill Types',
    )
    buildex_years_experience = fields.Integer(string='Years of Experience')
    buildex_jobs_linked_count = fields.Integer(compute='_compute_buildex_fundi_metrics', string='Jobs Linked')
    buildex_projects_handled_count = fields.Integer(compute='_compute_buildex_fundi_metrics', string='Projects Handled')
    buildex_customer_rating_avg = fields.Float(
        compute='_compute_buildex_fundi_metrics',
        string='Average Customer Rating',
        digits=(16, 2),
    )
    buildex_fundi_rank = fields.Selection(
        [
            ('starter', 'Starter'),
            ('trusted', 'Trusted'),
            ('elite', 'Elite'),
        ],
        compute='_compute_buildex_fundi_metrics',
        string='Fundi Rank',
    )
    buildex_fundi_score = fields.Integer(
        compute='_compute_buildex_fundi_metrics',
        string='Fundi Score',
    )

    @api.depends(
        'is_fundi',
        'buildex_years_experience',
        'buildex_skill_type_ids',
    )
    def _compute_buildex_fundi_metrics(self):
        sale_order_model = self.env['sale.order']
        project_model = self.env['buildex.project']
        feedback_model = self.env['buildex.feedback']

        for partner in self:
            if not partner.is_fundi:
                partner.buildex_jobs_linked_count = 0
                partner.buildex_projects_handled_count = 0
                partner.buildex_customer_rating_avg = 0.0
                partner.buildex_fundi_rank = False
                partner.buildex_fundi_score = 0
                continue

            partner.buildex_jobs_linked_count = sale_order_model.search_count([
                ('buildex_fundi_id', '=', partner.id),
            ])
            partner.buildex_projects_handled_count = project_model.search_count([
                ('fundi_id', '=', partner.id),
            ])
            feedbacks = feedback_model.search([
                ('fundi_id', '=', partner.id),
                ('fundi_satisfaction', '!=', False),
            ])
            if feedbacks:
                partner.buildex_customer_rating_avg = sum(
                    int(value) for value in feedbacks.mapped('fundi_satisfaction')
                ) / len(feedbacks)
            else:
                partner.buildex_customer_rating_avg = 0.0

            rating_component = min(int(partner.buildex_customer_rating_avg * 10), 50)
            experience_component = min((partner.buildex_years_experience or 0) * 4, 20)
            jobs_component = min(partner.buildex_jobs_linked_count * 2, 20)
            skills_component = min(len(partner.buildex_skill_type_ids) * 5, 10)
            partner.buildex_fundi_score = rating_component + experience_component + jobs_component + skills_component
            if partner.buildex_fundi_score >= 80:
                partner.buildex_fundi_rank = 'elite'
            elif partner.buildex_fundi_score >= 50:
                partner.buildex_fundi_rank = 'trusted'
            else:
                partner.buildex_fundi_rank = 'starter'

    @api.depends(
        'buildex_project_ids.stage_id',
        'buildex_feedback_ids.product_satisfaction',
        'buildex_feedback_ids.feedback_date',
        'buildex_followup_ids.state',
        'buildex_followup_ids.due_date',
        'buildex_next_expected_need_id',
    )
    def _compute_buildex_customer_metrics(self):
        today = fields.Date.context_today(self)
        order_model = self.env['sale.order']
        for partner in self:
            confirmed_orders = order_model.search([
                ('partner_id', 'child_of', partner.commercial_partner_id.ids),
                ('state', 'in', ('sale', 'done')),
            ])
            feedbacks = partner.buildex_feedback_ids.filtered(lambda feedback: feedback.product_satisfaction)
            followups = partner.buildex_followup_ids.filtered(
                lambda followup: followup.state not in ('done', 'cancelled')
            )
            overdue_followups = followups.filtered(lambda followup: followup.due_date and followup.due_date < today)

            latest_dates = partner.buildex_feedback_ids.mapped('feedback_date') + partner.buildex_followup_ids.mapped('due_date')
            latest_dates += [
                value.date() for value in partner.buildex_project_ids.mapped('write_date') if value
            ]
            latest_dates = [value for value in latest_dates if value]
            partner.buildex_last_activity_date = max(latest_dates) if latest_dates else False
            partner.buildex_pending_followup_count = len(followups)
            partner.buildex_total_sales_amount = sum(confirmed_orders.mapped('amount_total'))
            partner.buildex_one_time_buyer = len(confirmed_orders) == 1
            partner.buildex_high_value_customer = partner.buildex_total_sales_amount >= 500000

            score = 30
            score += min(len(partner.buildex_project_ids) * 8, 24)
            score += min(len(confirmed_orders) * 6, 18)
            score += min(int(partner.buildex_total_sales_amount / 100000) * 4, 16)
            if feedbacks:
                average_rating = sum(int(value) for value in feedbacks.mapped('product_satisfaction')) / len(feedbacks)
                score += int(average_rating * 4)
            if overdue_followups:
                score -= min(len(overdue_followups) * 10, 30)
            if partner.buildex_next_expected_need_id:
                score += 4
            score = max(0, min(score, 100))

            partner.buildex_customer_health_score = score
            if score >= 80:
                partner.buildex_customer_health_segment = 'excellent'
            elif score >= 60:
                partner.buildex_customer_health_segment = 'healthy'
            elif score >= 40:
                partner.buildex_customer_health_segment = 'monitor'
            else:
                partner.buildex_customer_health_segment = 'at_risk'
            partner.buildex_at_risk = partner.buildex_customer_health_segment == 'at_risk'

    @api.depends(
        'is_referrer',
        'referral_total_visits',
    )
    def _compute_buildex_influencer_metrics(self):
        order_model = self.env['sale.order']
        for partner in self:
            if not partner.is_referrer:
                partner.buildex_influencer_quality_score = 0
                partner.buildex_influencer_rank = False
                partner.buildex_referral_sale_count = 0
                partner.buildex_referral_revenue = 0.0
                continue

            referral_orders = order_model.search([
                ('referral_partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
            ])
            sale_count = len(referral_orders)
            revenue = sum(referral_orders.mapped('amount_total'))
            quality_score = min(sale_count * 10, 60) + min(int(revenue / 50000) * 5, 30)
            if getattr(partner, 'referral_total_visits', 0):
                quality_score += min(int(partner.referral_total_visits / 20) * 2, 10)
            quality_score = max(0, min(quality_score, 100))

            partner.buildex_referral_sale_count = sale_count
            partner.buildex_referral_revenue = revenue
            partner.buildex_influencer_quality_score = quality_score
            if quality_score >= 85:
                partner.buildex_influencer_rank = 'platinum'
            elif quality_score >= 65:
                partner.buildex_influencer_rank = 'gold'
            elif quality_score >= 40:
                partner.buildex_influencer_rank = 'silver'
            else:
                partner.buildex_influencer_rank = 'bronze'
