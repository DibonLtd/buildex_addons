# -*- coding: utf-8 -*-

# import logging
# import werkzeug
# import werkzeug.exceptions
# import werkzeug.utils
# import werkzeug.wrappers
# import werkzeug.wsgi
# # from twilio.rest import Client
# from odoo import http, _
# from odoo.http import request
# from odoo.exceptions import UserError
# from odoo.addons.web.controllers.home import Home
# from odoo.addons.mail.tools.discuss import get_twilio_credentials
# from odoo.addons.auth_signup.models.res_users import SignupError
# _logger = logging.getLogger(__name__)


# class AuthSignupHome(Home):
#     """Uses to signup with mobile number and
#     login with the same mobile number"""

#     @http.route('/web/signup-mobile', type='http', auth='public',
#                 website=True, sitemap=False)
#     def web_auth_signup_mobile(self, *args, **kw):
#         """Create new user with mobile number"""
#         qcontext = self.get_auth_signup_qcontext()
#         if kw.get('country_code') and kw.get('login_mobile'):
#             qcontext.update({'login': kw.get('country_code') + kw.get(
#                 'login_mobile')})
#             kw.update({'login': kw.get('country_code') + kw.get(
#                 'login_mobile')})
#         if not qcontext.get('token') and not qcontext.get('signup_enabled'):
#             raise werkzeug.exceptions.NotFound()
#         if 'error' not in qcontext and request.httprequest.method == 'POST':
#             try:
#                 self.do_signup(qcontext)
#                 user = request.env['res.users'].sudo().search(
#                     [('login', '=', qcontext['login'])])
#                 if user.partner_id and kw.get('signup_mobile'):
#                     user.partner_id.update({'email': ''})
#                     user.partner_id.update({'phone': qcontext['login']})
#                 return self.web_login(*args, **kw)
#             except UserError as e:
#                 qcontext['error'] = e.args[0]
#             except (SignupError, AssertionError) as e:
#                 if request.env["res.users"].sudo().search(
#                         [("login", "=", qcontext.get("login"))]):
#                     qcontext["error"] = _(
#                         "Another user is already registered "
#                         "using this Mobile Number.")
#                 else:
#                     _logger.error("%s", e)
#                     qcontext['error'] = _("Could not create a new account.")
#         response = request.render('signup_with_dibon_sms.signup_mobile', qcontext)
#         response.headers['X-Frame-Options'] = 'SAMEORIGIN'
#         response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
#         return response

#     @http.route('/web/login', type='http', auth="public", website=True)
#     def web_login(self, redirect=None, **kw):
#         """Update the parameters to login with mobile Number"""
#         request.params.update({'login': kw.get('login')})
#         return super().web_login(**kw)

#     @http.route('/web/send_otp', auth='public', type='json')
#     def web_send_otp(self, **kw):
#         """Sent OTP through SMS to the given number using twilio"""
#         (account_sid, auth_token) = get_twilio_credentials(request.env)
#         from_number = request.env['ir.config_parameter'].sudo().get_param(
#             'signup_with_dibon_sms.twilio_from_number')
#         if not account_sid or not auth_token or not from_number:
#             raise UserError(_('Twilio Credential are Required'))
#         client = Client(account_sid, auth_token)
#         message = client.messages.create(
#             to='+' + kw.get('country_code') + kw.get('mobile'),
#             from_=from_number,
#             body='Your Odoo verification code is:' + str(kw.get('otp')) +
#                  '.OTP valid till 2 minutes.'
#         )
#         _logger.info('Message successfully sent to your mobie number: %s',
#                      message.sid)

#     @http.route('/web/reset_password', type='http', auth='public',
#                 website=True, sitemap=False)
#     def web_auth_reset_password(self, *args, **kw):
#         """Update the email in user email field"""
#         if kw.get('login-mail'):
#             user = request.env['res.users'].sudo().search(
#                 [('login', '=', kw.get('login'))])
#             if user:
#                 user.email = kw.get('login-mail')
#         return super(AuthSignupHome, self).web_auth_reset_password(args, **kw)



# -*- coding: utf-8 -*-
#############################################################################
#
#    Dibon Consulting
#
#    Copyright (C) 2024-TODAY Dibon Consulting
#    Author: Gibeongideon
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
import random
import string
import time
import werkzeug.exceptions
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.addons.web.controllers.home import Home
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)

OTP_EXPIRY_SECONDS = 10 * 60  # 10 minutes

class MobileSignupRedirect(AuthSignupHome):

    @http.route('/web/signup', type='http', auth='none', sitemap=False)
    def web_auth_signup(self, *args, **kw):
        if not request.session.uid:
            query = url_encode(kw) if kw else ""
            target = '/web/signup-mobile'
            if query:
                target = f"{target}?{query}"
            return request.redirect(target)
        return super().web_auth_signup(*args, **kw)
    
    
class AuthSignupHome(Home):

    def _sanitize_redirect_target(self, redirect):
        if not redirect:
            return '/shop'
        redirect = redirect.strip()
        if redirect.startswith('/') and not redirect.startswith('//'):
            return redirect
        return '/shop'

    def _get_available_delivery_towns(self):
        kenya = request.env["res.country"].sudo().search([("code", "=", "KE")], limit=1)
        state_model = request.env["res.country.state"].sudo()
        if not kenya:
            return state_model
        domain = [("country_id", "=", kenya.id)]
        if "is_delivery_town" in state_model._fields:
            domain.append(("is_delivery_town", "=", True))
        return state_model.search(domain, order="name asc")

    # ----------------------------------------------------------------
    # STEP 1 – /mobile/signup  (mobile required, email optional)
    # ----------------------------------------------------------------
    @http.route('/mobile/signup', type='http', auth='public', website=True, methods=['GET'])
    def mobile_signup_step1(self, **kw):
        if not request.env.user._is_public():
            redirect_to = request.session.pop('post_signup_redirect', None)
            return request.redirect(redirect_to or '/')
        error_map = {
            'missing_mobile': "Please enter your mobile number.",
            'mobile_exists': "An account with this mobile number already exists. Please log in.",
            'mobile_registered': "mobile_registered",
            'email_exists': "An account with this email already exists. Please log in.",
            'invalid_email': "Please enter a valid email address.",
        }
        error_key = kw.get('error', '')
        return request.render('signup_with_dibon_sms.mobile_signup_step1', {
            'error': error_map.get(error_key, ''),
            'show_mobile_registered_popup': error_key == 'mobile_registered',
        })

    # ----------------------------------------------------------------
    # STEP 2 – send OTP
    # ----------------------------------------------------------------
    @http.route('/mobile/signup/send-otp', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def mobile_signup_send_otp(self, **post):
        country_code = (post.get('country_code') or '254').strip()
        mobile_raw = (post.get('login_mobile') or '').strip()
        email = (post.get('email') or '').strip().lower()

        if not mobile_raw:
            return request.redirect('/mobile/signup?error=missing_mobile')

        mobile_full = country_code + mobile_raw  # digits only, no +
        login = email if email else mobile_full

        # Validate email if provided
        if email and ('@' not in email or '.' not in email.split('@')[-1]):
            return request.redirect('/mobile/signup?error=invalid_email')

        # Check if mobile already registered (partner.mobile field)
        mobile_with_plus = '+' + mobile_full
        Partner = request.env['res.partner'].sudo()
        if Partner.search(['|', ('mobile', '=', mobile_with_plus), ('mobile', '=', mobile_full)], limit=1):
            return request.redirect('/mobile/signup?error=mobile_registered')

        # Check login (email or mobile) duplicate in users
        if request.env['res.users'].sudo().search([('login', '=', login)], limit=1):
            error = 'email_exists' if email else 'mobile_exists'
            return request.redirect(f'/mobile/signup?error={error}')

        otp = ''.join(random.choices(string.digits, k=4))
        request.session.update({
            'mobile_signup_otp': otp,
            'mobile_signup_otp_created': int(time.time()),
            'mobile_signup_mobile_full': mobile_full,
            'mobile_signup_mobile_raw': mobile_raw,
            'mobile_signup_country_code': country_code,
            'mobile_signup_email': email,
            'mobile_signup_login': login,
        })

        # Send via sms.sms (same working mechanism as signup_with_dibon_sms)
        mobile_with_plus = '+' + mobile_full
        message = 'Your verification code is: ' + otp + '. Valid for 10 minutes.'
        try:
            sms = request.env['sms.sms'].sudo().create({
                'number': mobile_with_plus,
                'body': message,
            })
            sms._send()
            _logger.info("[OTP] Sent to %s", mobile_with_plus)
        except Exception as exc:
            _logger.warning("[OTP] SMS failed for %s: %s", mobile_with_plus, exc)

        return request.redirect('/mobile/signup/verify')

    # ----------------------------------------------------------------
    # STEP 3 – OTP verify (GET)
    # ----------------------------------------------------------------
    @http.route('/mobile/signup/verify', type='http', auth='public', website=True, methods=['GET'])
    def mobile_signup_verify_get(self, **kw):
        if not request.session.get('mobile_signup_otp'):
            return request.redirect('/mobile/signup')
        error_map = {
            'invalid_otp': "Invalid OTP. Please try again.",
            'otp_expired': "OTP has expired. Please request a new one.",
        }
        return request.render('signup_with_dibon_sms.mobile_signup_verify', {
            'mobile': request.session.get('mobile_signup_mobile_full', ''),
            'error': error_map.get(kw.get('error'), ''),
        })

    # ----------------------------------------------------------------
    # STEP 3 – OTP verify (POST)
    # ----------------------------------------------------------------
    @http.route('/mobile/signup/verify', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def mobile_signup_verify_post(self, **post):
        otp_input = (post.get('otp') or '').strip()
        stored_otp = request.session.get('mobile_signup_otp')
        otp_created = request.session.get('mobile_signup_otp_created', 0)

        if not stored_otp:
            return request.redirect('/mobile/signup')

        if int(time.time()) - int(otp_created) > OTP_EXPIRY_SECONDS:
            request.session.pop('mobile_signup_otp', None)
            return request.redirect('/mobile/signup/verify?error=otp_expired')

        if otp_input != stored_otp:
            return request.redirect('/mobile/signup/verify?error=invalid_otp')

        # Mobile is free — clear OTP keys, set verified flag, keep mobile/email for details step
        request.session.pop('mobile_signup_otp', None)
        request.session.pop('mobile_signup_otp_created', None)
        request.session['mobile_signup_verified'] = True

        return request.redirect('/web/signup-mobile')

    # ----------------------------------------------------------------
    # STEP 3 – resend OTP
    # ----------------------------------------------------------------
    @http.route('/mobile/signup/resend-otp', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def mobile_signup_resend_otp(self, **post):
        mobile_full = request.session.get('mobile_signup_mobile_full')
        if not mobile_full:
            return request.redirect('/mobile/signup')

        otp = ''.join(random.choices(string.digits, k=4))
        request.session['mobile_signup_otp'] = otp
        request.session['mobile_signup_otp_created'] = int(time.time())

        mobile_with_plus = '+' + mobile_full
        message = 'Your verification code is: ' + otp + '. Valid for 10 minutes.'
        try:
            sms = request.env['sms.sms'].sudo().create({
                'number': mobile_with_plus,
                'body': message,
            })
            sms._send()
        except Exception as exc:
            _logger.warning("[OTP] Resend failed for %s: %s", mobile_with_plus, exc)

        return request.redirect('/mobile/signup/verify')

    # ----------------------------------------------------------------
    # STEP 4 – full details form  /web/signup-mobile
    # ----------------------------------------------------------------
    @http.route('/web/signup-mobile', type='http', auth='public',
                website=True, sitemap=False)
    def web_auth_signup_mobile(self, *args, **kw):
        otp_verified = request.session.get('mobile_signup_verified', False)

        qcontext = self.get_auth_signup_qcontext()
        qcontext["redirect"] = kw.get("redirect")
        qcontext["available_delivery_towns"] = self._get_available_delivery_towns()
        qcontext["default_delivery_town_id"] = kw.get("default_delivery_town_id")
        qcontext["otp_verified"] = otp_verified

        # Pre-fill from OTP session when coming from verified flow
        if otp_verified:
            session_email = request.session.get('mobile_signup_email', '')
            session_mobile_raw = request.session.get('mobile_signup_mobile_raw', '')
            session_country_code = request.session.get('mobile_signup_country_code', '254')
            session_login = request.session.get('mobile_signup_login', '')
            qcontext['login'] = session_login
            qcontext['signup_email'] = session_email
            qcontext['prefilled_mobile_raw'] = session_mobile_raw
            qcontext['prefilled_country_code'] = session_country_code
        else:
            if kw.get('signup_email'):
                qcontext.update({'login': kw.get('signup_email')})
                kw.update({'login': kw.get('signup_email')})

        # Only block access if not from OTP flow and no token/signup_enabled
        if not otp_verified and not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            # For OTP-verified flow, pull login from session (hidden field may be empty if tampered)
            if otp_verified and not qcontext.get('login'):
                qcontext['login'] = request.session.get('mobile_signup_login', '')
            try:
                self.do_signup(qcontext)
                user = request.env['res.users'].sudo().search(
                    [('login', '=', qcontext['login'])])
                if user.partner_id:
                    # Mobile: use session value for OTP flow, form value otherwise
                    if otp_verified:
                        full_mobile = request.session.get('mobile_signup_mobile_full', '')
                    else:
                        full_mobile = (
                            kw.get('country_code', '') + kw.get('login_mobile', '')
                        ).strip()
                    partner_vals = {}
                    if full_mobile:
                        partner_vals['mobile'] = full_mobile

                    if kw.get('comm_mode_call'):
                        partner_vals['comm_mode_call'] = True
                    if kw.get('comm_mode_whatsapp'):
                        partner_vals['comm_mode_whatsapp'] = True
                    if kw.get('comm_mode_sms'):
                        partner_vals['comm_mode_sms'] = True

                    try:
                        lat = float(kw.get('visitor_latitude') or 0)
                        lng = float(kw.get('visitor_longitude') or 0)
                        if lat and lng:
                            partner_vals['visitor_latitude'] = lat
                            partner_vals['visitor_longitude'] = lng
                        loc_source = kw.get('visitor_location_source', '').strip()
                        if loc_source in ('gps', 'network', 'ip'):
                            partner_vals['visitor_location_source'] = loc_source
                        visitor_city = kw.get('visitor_city', '').strip()
                        if visitor_city:
                            partner_vals['visitor_city'] = visitor_city
                    except (TypeError, ValueError):
                        pass

                    # Referral attribution
                    ref_code = request.session.get('referral_code')
                    if ref_code:
                        influencer = request.env['res.partner'].sudo().search([
                            ('referral_code', '=', ref_code),
                            ('is_referrer', '=', True),
                        ], limit=1)
                        if influencer and influencer != user.partner_id:
                            partner_vals['referred_by_id'] = influencer.id

                    if partner_vals:
                        user.partner_id.write(partner_vals)

                town_id = kw.get("default_delivery_town_id")
                if town_id and user.partner_id:
                    try:
                        town = request.env["res.country.state"].sudo().browse(
                            int(town_id)
                        ).exists()
                    except (TypeError, ValueError):
                        town = request.env["res.country.state"]
                    if town:
                        user.partner_id.write({
                            "country_id": town.country_id.id,
                            "state_id": town.id,
                        })

                # Authenticate
                credential = {
                    'login': qcontext.get('login'),
                    'password': qcontext.get('password'),
                    'type': 'password',
                }
                try:
                    request.session.authenticate(request.db, credential)
                except Exception:
                    pass

                # Clear OTP session data
                for key in ('mobile_signup_verified', 'mobile_signup_mobile_full',
                            'mobile_signup_mobile_raw', 'mobile_signup_country_code',
                            'mobile_signup_email', 'mobile_signup_login'):
                    request.session.pop(key, None)

                redirect_target = self._sanitize_redirect_target(
                    request.session.pop('post_signup_redirect', None) or kw.get('redirect')
                )
                return request.redirect(redirect_target)
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError):
                if request.env["res.users"].sudo().search(
                        [("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _(
                        "Another user is already registered using this mobile/email.")
                else:
                    qcontext['error'] = _("Could not create a new account.")

        response = request.render('signup_with_dibon_sms.signup_mobile', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    # @http.route('/web/send_otp', auth='public', type='json')
    # def web_send_otp(self, **kw):
    #     """Send OTP using Odoo SMS (handled by dibon_sms provider)"""

    #     mobile = '+' + kw.get('country_code') + kw.get('mobile')
    #     message_body = (
    #         'Your App verification code is:' +
    #         str(kw.get('otp')) +
    #         '. OTP valid till 2 minutes.'
    #     )

    #     _logger.warning("OTP for %s: %s", mobile, kw.get('otp'))

    #     sms = request.env['sms.sms'].sudo().create({
    #         'number': mobile,
    #         'body': message_body,
    #     })

    #     try:
    #         sms._send()
    #     except Exception as e:
    #         _logger.error("SMS sending failed: %s", str(e))

    #     return {'status': 'sent'}
    

    @http.route('/web/send_otp', auth='public', type='json')
    def web_send_otp(self, **kw):
        """Send OTP using Odoo SMS (handled by dibon_sms provider)"""

        country_code = kw.get('country_code')
        mobile_raw = kw.get('mobile')
        otp = kw.get('otp')

        mobile = '+' + country_code + mobile_raw

        message_body = (
            'Your App verification code is: ' +
            str(otp) +
            '. OTP valid till 2 minutes.'
        )

        # ✅ Log incoming request
        _logger.info("OTP Request Received | Mobile: %s | OTP: %s", mobile, otp)

        try:
            # ✅ Create SMS record
            sms = request.env['sms.sms'].sudo().create({
                'number': mobile,
                'body': message_body,
            })

            _logger.info(
                "SMS Record Created | ID: %s | Number: %s | State: %s",
                sms.id, sms.number, sms.state
            )

            # ✅ Attempt sending
            sms._send()

            _logger.info(
                "SMS Send Triggered | ID: %s | Final State: %s",
                sms.id, sms.state
            )

            return {'status': 'sent'}

        except Exception as e:
            _logger.error(
                "SMS Sending Failed | Mobile: %s | Error: %s",
                mobile, str(e)
            )
            return {'status': 'failed', 'error': str(e)}
