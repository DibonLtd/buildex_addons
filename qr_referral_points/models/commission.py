from odoo import models, fields, api


class InfluencerCommission(models.Model):
    _name = 'influencer.commission'
    _description = 'Influencer Commission'

    partner_id = fields.Many2one('res.partner', required=True)
    sale_order_id = fields.Many2one('sale.order')
    invoice_id = fields.Many2one('account.move')

    base_amount = fields.Monetary()
    commission_amount = fields.Monetary(string="Gross Commission (IC)")

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('batched', 'Batched'),
        ('paid', 'Paid'),
    ], default='draft')

    batch_id = fields.Many2one('influencer.commission.batch')

    commission_type = fields.Selection([
        ('direct', 'Direct Sale Commission'),
        ('topline', 'Topline Mentorship Bonus'),
    ], default='direct', string='Commission Type', required=True)

    topline_source_commission_id = fields.Many2one(
        'influencer.commission',
        string='Source Commission',
        help='The direct commission that triggered this topline bonus',
        ondelete='cascade',
    )

    # ── Net earnings breakdown: IC − TB − Tax ──────────────────────────────
    topline_deduction = fields.Monetary(
        string="Topline Deduction",
        compute='_compute_net_amount', store=True,
        help="Amount deducted from IC and paid to the topline mentor",
    )
    tax_amount = fields.Monetary(
        string="Withholding Tax",
        compute='_compute_net_amount', store=True,
        help="Tax deducted from taxable amount — reflected on the payout bill",
    )
    net_amount = fields.Monetary(
        string="Net Earnings",
        compute='_compute_net_amount', store=True,
        help="IC − Topline Deduction − Tax = amount credited to influencer wallet",
    )

    @api.depends(
        'commission_amount', 'commission_type',
        'partner_id.topline_id',
        'partner_id.commission_plan_id.topline_bonus_rate',
        'partner_id.commission_plan_id.withholding_tax_rate',
    )
    def _compute_net_amount(self):
        fixed_wht = self.env['influencer.commission.plan']._get_withholding_tax_rate()
        for rec in self:
            plan = rec.partner_id.commission_plan_id
            wht = fixed_wht
            tb_rate = plan.topline_bonus_rate if plan else 10.0

            if rec.commission_type == 'topline':
                # Topline bonus: no topline deduction, only tax
                rec.topline_deduction = 0.0
                rec.tax_amount = rec.commission_amount * wht / 100
                rec.net_amount = rec.commission_amount - rec.tax_amount
            else:
                # Direct commission: deduct topline bonus then tax
                tb = rec.commission_amount * tb_rate / 100 if rec.partner_id.topline_id else 0.0
                rec.topline_deduction = tb
                taxable = rec.commission_amount - tb
                rec.tax_amount = taxable * wht / 100
                rec.net_amount = taxable - rec.tax_amount

    # ── Approve ─────────────────────────────────────────────────────────────
    def action_approve(self):
        for rec in self:
            if rec.state == 'approved':
                continue

            rec.state = 'approved'

            # Credit influencer wallet with NET amount (after topline deduction + tax)
            existing_credit = self.env['influencer.wallet.transaction'].search([
                ('commission_id', '=', rec.id),
                ('transaction_type', '=', 'credit'),
            ], limit=1)

            if not existing_credit:
                self.env['influencer.wallet.transaction'].create({
                    'partner_id': rec.partner_id.id,
                    'transaction_type': 'credit',
                    'amount': rec.net_amount,
                    'commission_id': rec.id,
                })

            # Auto-create topline bonus for direct commissions only
            if rec.commission_type == 'direct':
                topline = rec.partner_id.topline_id
                if topline and not self.env['influencer.commission'].search([
                    ('topline_source_commission_id', '=', rec.id)
                ], limit=1):
                    plan = rec.partner_id.commission_plan_id
                    tb_rate = plan.topline_bonus_rate if plan else 10.0
                    bonus = rec.commission_amount * tb_rate / 100

                    topline_comm = self.env['influencer.commission'].create({
                        'partner_id': topline.id,
                        'sale_order_id': rec.sale_order_id.id,
                        'invoice_id': rec.invoice_id.id,
                        'base_amount': rec.commission_amount,
                        'commission_amount': bonus,
                        'currency_id': rec.currency_id.id,
                        'commission_type': 'topline',
                        'topline_source_commission_id': rec.id,
                        'state': 'approved',
                    })
                    # Topline wallet credited with their net amount (bonus minus their own tax)
                    self.env['influencer.wallet.transaction'].create({
                        'partner_id': topline.id,
                        'transaction_type': 'credit',
                        'amount': topline_comm.net_amount,
                        'commission_id': topline_comm.id,
                    })
