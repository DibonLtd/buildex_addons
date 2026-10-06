
from odoo import models, fields, api

class WalletTransaction(models.Model):
    _name = 'influencer.wallet.transaction'
    _description = 'Influencer Wallet Ledger'

    partner_id = fields.Many2one('res.partner', required=True)

    transaction_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ], required=True)

    amount = fields.Monetary(required=True)

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    commission_id = fields.Many2one('influencer.commission')
    batch_id = fields.Many2one('influencer.commission.batch')




    def _check_auto_payout(self):
        partner = self.partner_id
        plan = partner.commission_plan_id  # assuming partner linked to plan

        if not plan or not plan.auto_payout_enabled:
            return

        if partner.wallet_balance < plan.auto_payout_minimum:
            return

        # Create Batch
        batch = self.env['influencer.commission.batch'].create({
            'name': f'Auto Payout - {partner.name}',
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })

        commissions = self.env['influencer.commission'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'approved'),
            ('batch_id', '=', False),
        ])

        commissions.write({
            'batch_id': batch.id,
            'state': 'batched'
        })

        batch.action_create_vendor_bills()


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.transaction_type == 'credit':
                record._check_auto_payout()

        return records

