from odoo import models, fields, api
from odoo.http import request
import logging
import time

_logger = logging.getLogger(__name__)  # Logger for this module
REFERRAL_SESSION_TTL_SECONDS = 90 * 24 * 60 * 60

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    referral_partner_id = fields.Many2one('res.partner', string="Referral Partner", index=True, ondelete='set null')

    is_referral_order = fields.Boolean(default=False)
    referral_code = fields.Char(string='Referral Code')

    influencer_order_stage = fields.Selection(
        selection=[
            ('ordered', 'Ordered'),
            ('dispatched', 'Dispatched'),
            ('delivered', 'Delivered'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Paid'),
        ],
        string='Stage',
        compute='_compute_influencer_order_stage',
        store=True,
        compute_sudo=True,
        index=True,
    )

    @api.depends(
        'state',
        'picking_ids.state',
        'invoice_ids.state',
        'invoice_ids.payment_state',
        'invoice_ids.move_type',
    )
    def _compute_influencer_order_stage(self):
        for order in self:
            if order.state not in ('sale', 'done'):
                order.influencer_order_stage = False
                continue
            invoices = order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
            paid_inv = invoices.filtered(lambda m: m.payment_state in ('paid', 'in_payment'))
            posted_inv = invoices.filtered(lambda m: m.state == 'posted')
            draft_inv = invoices.filtered(lambda m: m.state == 'draft')
            if paid_inv:
                order.influencer_order_stage = 'paid'
            elif posted_inv:
                order.influencer_order_stage = 'invoiced'
            elif draft_inv:
                order.influencer_order_stage = 'delivered'
            elif order.picking_ids.filtered(lambda p: p.state == 'done'):
                order.influencer_order_stage = 'dispatched'
            else:
                order.influencer_order_stage = 'ordered'

    @api.model_create_multi
    def create(self, vals_list):
        # Log session before creating orders
        # if request and hasattr(request, 'session'):
        _logger.info("Session before creating sale order: %s", dict(request.session.items()))
        
        for vals in vals_list:
            # Get referral code from session
            ref_code = False
            if request and hasattr(request, 'session'):
                ref_code = request.session.get('referral_code')
                ref_set_at = request.session.get('referral_code_set_at')
                try:
                    ref_set_at = int(ref_set_at) if ref_set_at else 0
                except (TypeError, ValueError):
                    ref_set_at = 0

                if ref_code and (not ref_set_at or (int(time.time()) - ref_set_at) > REFERRAL_SESSION_TTL_SECONDS):
                    request.session.pop('referral_code', None)
                    request.session.pop('referral_code_set_at', None)
                    ref_code = False
            if ref_code:
                partner = self.env['res.partner'].search([('referral_code', '=', ref_code)], limit=1)
                order_partner = self.env['res.partner'].browse(vals.get('partner_id')).commercial_partner_id
                if partner and partner.commercial_partner_id != order_partner:
                    vals['referral_code'] = ref_code
                    vals['is_referral_order'] = True
                    vals['referral_partner_id'] = partner.id
                else:
                    _logger.info(
                        "Blocked self-referral on sale order for partner %s with code %s",
                        order_partner.id if order_partner else False,
                        ref_code,
                    )

        # Remove referral code from session after first use
        # if request and hasattr(request, 'session'):
        #     _logger.info("Removing referral code from session: %s", request.session.get('referral_code'))
        #     request.session.pop('referral_code', None)

        # Log the vals that will be used to create the sale order
        _logger.info("Sale order values being created: %s", vals_list)

        return super(SaleOrder, self).create(vals_list)
    
    
        
    # def _generate_commission(self):
    #     for order in self:

    #         partner = order.referral_partner_id
    #         if not partner or not partner.commission_plan_id:
    #             continue

    #         plan = partner.commission_plan_id
    #         total_commission = 0.0

    #         for line in order.order_line:
    #             category = line.product_id.categ_id

    #             rule = plan.rule_ids.filtered(
    #                 lambda r: r.categ_id == category
    #             )[:1]

    #             rate = rule.rate if rule else plan.default_rate

    #             total_commission += line.price_total * rate / 100

    #         if total_commission <= 0:
    #             continue

    #         self.env['influencer.commission'].create({
    #             'partner_id': partner.id,
    #             'sale_order_id': order.id,
    #             'base_amount': order.amount_total,
    #             'commission_amount': total_commission,
    #             'currency_id': order.currency_id.id,
    #             'state': 'approved'
    #         })
