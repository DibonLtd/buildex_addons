import time
import logging
from datetime import timedelta

from odoo import models, fields

_logger = logging.getLogger(__name__)

_REFERRAL_COOKIE = 'blx_ref'
_REFERRAL_COOKIE_SET_AT = 'blx_ref_set_at'
_REFERRAL_SESSION_TTL_SECONDS = 90 * 24 * 60 * 60


class IrHttp(models.AbstractModel):
    """Restore the visitor referral code from cookie or partner DB into the
    server-side session on every request, so the commission attribution
    survives cross-device and cross-browser access."""

    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        try:
            from odoo.http import request as req
            session = req.session

            ref = session.get('referral_code', '').strip()
            session_set_at = session.get('referral_code_set_at')
            now_ts = int(time.time())

            try:
                session_set_at = int(session_set_at) if session_set_at else 0
            except (TypeError, ValueError):
                session_set_at = 0

            if ref and (not session_set_at or (now_ts - session_set_at) > _REFERRAL_SESSION_TTL_SECONDS):
                session.pop('referral_code', None)
                session.pop('referral_code_set_at', None)
                ref = ''

            if not ref:
                # 1. Try browser cookie first (survives browser restarts)
                cookie_ref = req.httprequest.cookies.get(_REFERRAL_COOKIE, '').strip()
                cookie_set_at = req.httprequest.cookies.get(_REFERRAL_COOKIE_SET_AT, '').strip()
                try:
                    cookie_set_at = int(cookie_set_at) if cookie_set_at else 0
                except (TypeError, ValueError):
                    cookie_set_at = 0

                if cookie_ref and cookie_set_at and (now_ts - cookie_set_at) <= _REFERRAL_SESSION_TTL_SECONDS:
                    ref = cookie_ref
                    session['referral_code'] = ref
                    session['referral_code_set_at'] = cookie_set_at
                    _logger.info("Referral code '%s' restored from cookie to session", ref)

                # 2. Try partner DB (cross-device: different browser / phone)
                elif not req.env.user._is_public():
                    partner = req.env.user.partner_id.sudo()
                    db_code = partner.tracked_referral_code
                    expiry = partner.tracked_referral_code_expiry
                    if db_code and expiry and expiry > fields.Datetime.now():
                        ref = db_code
                        expiry_dt = fields.Datetime.to_datetime(expiry)
                        set_at_dt = expiry_dt - timedelta(seconds=_REFERRAL_SESSION_TTL_SECONDS)
                        session['referral_code'] = ref
                        session['referral_code_set_at'] = int(set_at_dt.timestamp())
                        _logger.info(
                            "Referral code '%s' restored from DB to session for %s",
                            ref, partner.name,
                        )

            # 3. If we now have a referral code and the user is authenticated,
            #    make sure referred_by_id is set on their partner (catches all
            #    signup paths including standard /web/signup).
            if ref and not req.env.user._is_public():
                partner = req.env.user.partner_id.sudo()
                if not partner.referred_by_id:
                    influencer = req.env['res.partner'].sudo().search([
                        ('referral_code', '=', ref),
                        ('is_referrer', '=', True),
                    ], limit=1)
                    if influencer and influencer.id != partner.id:
                        partner.write({'referred_by_id': influencer.id})
                        _logger.info(
                            "Set referred_by_id=%s on partner %s via session referral code",
                            influencer.name, partner.name,
                        )

        except Exception:
            pass  # never break a request over session restoration

        return super()._dispatch(endpoint)
