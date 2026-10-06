import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    bank_till_payment_reference = fields.Char(
        string='M-PESA / Equity Reference',
        help='Confirmation code submitted by the customer after sending money via Paybill.',
        copy=False,
    )

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of payment to find the transaction based on bank_till data."""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'bank_till' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'bank_till')])
        if not tx:
            raise ValidationError(
                "Bank Paybill: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """Override of payment to process bank_till transaction.

        Sets the transaction to pending, waiting for manual confirmation by staff.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'bank_till':
            return

        self.provider_reference = f'bank_till-{self.reference}'

        # Save customer-provided payment reference on the transaction and linked orders
        customer_ref = notification_data.get('payment_reference', '')
        if customer_ref:
            self.bank_till_payment_reference = customer_ref
            self.sale_order_ids.write({'bank_till_payment_reference': customer_ref})

        # Always set to pending — staff will confirm once Paybill payment is verified
        self._set_pending()

        # Confirm any linked sale orders that are still quotations so they become
        # confirmed orders immediately (required for referral/influencer association).
        # The payment itself remains pending until staff manually verifies the M-PESA ref.
        draft_orders = self.sale_order_ids.filtered(lambda o: o.state in ('draft', 'sent'))
        if draft_orders:
            draft_orders.with_context(
                mail_notrack=True,
                mail_auto_subscribe_no_notify=True,
            ).action_confirm()

    def action_confirm_bank_till_payment(self):
        """Manually confirm a pending Equity/bank_till payment.

        Called by backend staff after verifying the M-PESA reference against the
        Equity Bank statement. Sets the transaction to done, which triggers Odoo's
        standard flow to mark the linked sale order as paid.
        """
        for tx in self:
            if tx.provider_code != 'bank_till':
                raise UserError(_("This action is only available for Equity Paybill transactions."))
            if tx.state != 'pending':
                raise UserError(
                    _("Transaction %s is not in a pending state (current: %s).", tx.reference, tx.state)
                )
            if not tx.bank_till_payment_reference:
                raise UserError(
                    _("Cannot confirm transaction %s: no M-PESA reference on record.", tx.reference)
                )
            tx._set_done()
            _logger.info(
                "Bank Paybill: transaction %s manually confirmed by %s (M-PESA ref: %s)",
                tx.reference, self.env.user.name, tx.bank_till_payment_reference,
            )
