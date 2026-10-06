from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _invoice_paid_hook(self):
        """Called by Odoo core when an invoice transitions to paid/in_payment state.
        Covers all payment paths: register payment, bank reconciliation, zero-amount post.
        """
        super()._invoice_paid_hook()
        self._generate_commission_from_invoice()

    def _generate_commission_from_invoice(self):
        _logger.info("Starting _generate_commission_from_invoice for %d moves", len(self))
        Commission = self.env['influencer.commission']

        for move in self:
            if move.move_type != 'out_invoice' or move.payment_state not in ('paid', 'in_payment'):
                _logger.info("Skipping move %s (type: %s, payment_state: %s)", move.name, move.move_type, move.payment_state)
                continue

            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            _logger.info("Found %d sale orders linked to invoice %s", len(sale_orders), move.name)

            for order in sale_orders:
                partner = order.referral_partner_id
                if not partner or not partner.commission_plan_id:
                    _logger.info("Order %s has no referral partner or commission plan, skipping", order.name)
                    continue

                if partner.commercial_partner_id == order.partner_id.commercial_partner_id:
                    _logger.info(
                        "Skipping self-referral commission for order %s and partner %s",
                        order.name,
                        partner.id,
                    )
                    continue

                # Policy: commission requires payment + goods delivered
                deliveries_done = order.picking_ids.filtered(
                    lambda p: p.state == 'done'
                )
                if not deliveries_done:
                    _logger.info("Order %s has no completed delivery, skipping commission", order.name)
                    continue

                existing = Commission.search([
                    ('sale_order_id', '=', order.id),
                    ('invoice_id', '=', move.id)
                ], limit=1)

                if existing:
                    _logger.info("Commission already exists for order %s and invoice %s, skipping", order.name, move.name)
                    continue

                plan = partner.commission_plan_id
                total_commission = 0.0

                related_lines = move.invoice_line_ids.filtered(
                    lambda l: order in l.sale_line_ids.mapped('order_id')
                )
                _logger.info("Order %s has %d related invoice lines", order.name, len(related_lines))

                for inv_line in related_lines:
                    product = inv_line.product_id
                    rate = plan._get_rate_for_product(product)
                    total_commission += inv_line.price_subtotal * rate / 100

                if total_commission <= 0:
                    _logger.info("Total commission for order %s is zero, skipping", order.name)
                    continue

                Commission.create({
                    'partner_id': partner.id,
                    'sale_order_id': order.id,
                    'invoice_id': move.id,
                    'base_amount': move.amount_total,
                    'commission_amount': total_commission,
                    'currency_id': move.currency_id.id,
                    'state': 'draft'
                })
                _logger.info("Commission created for order %s, amount: %s", order.name, total_commission)

                # Recompute influencer stage
                order.sudo()._compute_influencer_order_stage()
