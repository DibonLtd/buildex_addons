# from odoo import http
# from odoo.http import request
# import logging

# _logger = logging.getLogger(__name__)

# class WebsiteReferral(http.Controller):

#     @http.route(['/shop', '/shop/<path:subpath>'], type='http', auth='public', website=True)
#     def shop_referral(self, subpath=None, **kwargs):
#         ref = kwargs.get('ref')
#         _logger.info("RRRRRRRRRRRRRR code added to session: %s", ref)
#         if ref:
#             # Persist referral code in session
#             request.session['referral_code'] = ref
#             _logger.info("Referral code added to session: %s", ref)
#             _logger.info("Session now: %s", dict(request.session.items()))
#             # Redirect to remove ?ref from URL
#             return request.redirect('/shop' if not subpath else f'/shop/{subpath}')

#         # Log session for debugging
#         _logger.info("Session on /shop: %s", dict(request.session.items()))

#         # Render shop normally
#         return http.request.render('website_sale.products', {})


from odoo import http
from odoo.http import request
import logging
import time
from urllib.parse import quote, urlencode

_logger = logging.getLogger(__name__)
REFERRAL_SESSION_TTL_SECONDS = 90 * 24 * 60 * 60

class WebsiteReferral(http.Controller):

    @http.route(['/shop', '/shop/<path:subpath>'], type='http', auth='public', website=True)
    def shop_referral(self, subpath=None, **kwargs):

        ref = kwargs.get('ref')
        session = request.session
        target_shop_url = '/shop' if not subpath else f'/shop/{subpath}'
        clean_params = {k: v for k, v in kwargs.items() if k != 'ref'}
        if clean_params:
            target_shop_url = f"{target_shop_url}?{urlencode(clean_params)}"

        # ----------------------------------------------------
        # 1️⃣ If referral in URL → store in session
        # ----------------------------------------------------
        if ref:
            referral_partner = request.env['res.partner'].sudo().search([
                ('referral_code', '=', ref),
                ('is_referrer', '=', True),
            ], limit=1)

            current_partner = request.env.user.partner_id.commercial_partner_id
            if (
                referral_partner
                and not request.env.user._is_public()
                and referral_partner.commercial_partner_id == current_partner
            ):
                session.pop('referral_code', None)
                session.pop('referral_code_set_at', None)
                _logger.info(
                    "Blocked self-referral for partner %s using code %s",
                    current_partner.id,
                    ref,
                )
                return request.redirect(target_shop_url)

            session['referral_code'] = ref
            session['referral_code_set_at'] = int(time.time())
            _logger.info("Referral code added to session: %s", ref)

            # Public users should signup first, then continue to shop.
            if request.env.user._is_public():
                signup_redirect = '/web/signup?redirect=%s&from_referral=1' % quote(target_shop_url, safe='')
                _logger.info("Public referral visitor redirected to signup first.")
                return request.redirect(signup_redirect)

            # Logged users: redirect to clean URL (remove ?ref=)
            return request.redirect(target_shop_url)

        # ----------------------------------------------------
        # 2️⃣ Validate session referral token (must exist and be fresh)
        # ----------------------------------------------------
        referral_code = session.get('referral_code')
        referral_set_at = session.get('referral_code_set_at')
        now_ts = int(time.time())

        try:
            referral_set_at = int(referral_set_at) if referral_set_at else 0
        except (TypeError, ValueError):
            referral_set_at = 0

        is_expired = not referral_set_at or (now_ts - referral_set_at) > REFERRAL_SESSION_TTL_SECONDS
        if not referral_code or is_expired:
            session.pop('referral_code', None)
            session.pop('referral_code_set_at', None)
            session.pop('influencer_access', None)  # cleanup old flag from previous logic
            _logger.info("Blocked public access to /shop: referral token missing/expired")
            return request.redirect('/')

        # ----------------------------------------------------
        # 3️⃣ If session valid but user is public → force signup
        # ----------------------------------------------------
        if request.env.user._is_public():
            signup_redirect = '/web/signup?redirect=%s&from_referral=1' % quote(target_shop_url, safe='')
            _logger.info("Public user on /shop with valid referral. Redirecting to signup.")
            return request.redirect(signup_redirect)

        # ----------------------------------------------------
        # 4️⃣ Logged in + session valid → render shop
        # ----------------------------------------------------
        _logger.info("Influencer access granted. Session: %s", dict(session.items()))

        return request.render('website_sale.products', {})
