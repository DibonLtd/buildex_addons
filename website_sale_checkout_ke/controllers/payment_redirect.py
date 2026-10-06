from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.http import request, route


class PaymentStatusRedirect(PaymentPortal):
    """Dedicated controller that overrides /payment/status.

    Inherits ONLY from PaymentPortal to avoid MRO conflicts with WebsiteSale.
    Redirects straight to our post-payment technician question page.
    """

    @route('/payment/status', type='http', auth='public', website=True, sitemap=False)
    def payment_status(self, **kwargs):
        return request.redirect('/shop/post_payment')
