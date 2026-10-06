from odoo import http
from odoo.http import request


class PaymentBankTillController(http.Controller):
    _process_url = '/payment/bank_till/process'

    @http.route(_process_url, type='json', auth='public')
    def bank_till_process_payment(self, **data):
        """Process the bank till payment form submission.

        Expects: reference, payment_reference (customer-provided Paybill transaction code).
        Sets transaction to pending for manual staff verification.
        """
        if not data.get('payment_reference', '').strip():
            return {'error': 'M-PESA reference is required.'}
        request.env['payment.transaction'].sudo()._handle_notification_data('bank_till', data)
