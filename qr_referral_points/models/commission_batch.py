from odoo import models, fields
from collections import defaultdict


class CommissionBatch(models.Model):
    _name = 'influencer.commission.batch'
    _description = 'Influencer Commission Batch'

    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    commission_ids = fields.One2many(
        'influencer.commission',
        'batch_id'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('batched', 'Batched'),
        ('billed', 'Vendor Bills Created'),
        ('paid', 'Paid')
    ], default='draft')

    def action_generate(self):
        for batch in self:
            commissions = self.env['influencer.commission'].search([
                ('state', '=', 'approved'),
                ('batch_id', '=', False),
                ('create_date', '>=', batch.date_from),
                ('create_date', '<=', batch.date_to),
            ])
            commissions.write({'batch_id': batch.id, 'state': 'batched'})
            batch.state = 'batched'

    def action_create_vendor_bills(self):
        fixed_wht = self.env['influencer.commission.plan']._get_withholding_tax_rate()
        for batch in self:
            grouped = defaultdict(list)
            for commission in batch.commission_ids:
                grouped[commission.partner_id].append(commission)

            for partner, commissions in grouped.items():
                gross = sum(c.commission_amount for c in commissions)
                topline_deduction = sum(c.topline_deduction for c in commissions)
                tax = sum(c.tax_amount for c in commissions)
                net = sum(c.net_amount for c in commissions)

                lines = [(0, 0, {
                    'name': f'Commission — {batch.name}',
                    'quantity': 1,
                    'price_unit': gross,
                })]

                if topline_deduction:
                    lines.append((0, 0, {
                        'name': f'Less: Topline Mentor Deduction',
                        'quantity': 1,
                        'price_unit': -topline_deduction,
                    }))

                if tax:
                    lines.append((0, 0, {
                        'name': f'Less: Withholding Tax ({fixed_wht}%)',
                        'quantity': 1,
                        'price_unit': -tax,
                    }))

                bill = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': lines,
                })
                bill.action_post()

                # Debit wallet by net payout amount
                self.env['influencer.wallet.transaction'].create({
                    'partner_id': partner.id,
                    'transaction_type': 'debit',
                    'amount': net,
                    'batch_id': batch.id,
                })

            batch.state = 'billed'
