import base64

from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools.float_utils import float_round
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import time
from odoo.addons.qr_referral_points.models.referral_visit_log import (
    _lookup_location,
    InfluencerReferralVisitLog,
)


_logger = logging.getLogger(__name__)
REFERRAL_SESSION_TTL_SECONDS = 90 * 24 * 60 * 60
REFERRAL_COOKIE_NAME = 'blx_ref'
REFERRAL_COOKIE_SET_AT_NAME = 'blx_ref_set_at'


class SignupRedirectFix(http.Controller):

    @http.route('/business-details', auth='user', website=True)
    def bypass_business_details(self, **kw):
        return request.redirect('/influencer/apply')


class InfluencerPortal(CustomerPortal):    

    def _my_menu_links(self, portal_menu, user, **kwargs):
        """Override to add custom link in /my menu"""
        menu_links = super()._my_menu_links(portal_menu, user, **kwargs)
        # Add Influencer link
        menu_links.append({
            'name': 'Influencer Program',
            'url': '/my/influencer',
            'icon': 'fa-users',  # optional, you can choose FontAwesome icon
        })
        return menu_links

class InfluencerController(http.Controller):

    @http.route(['/referral'], type='http', auth='public', website=True)
    def capture_referral(self, **kwargs):
        """
        Capture referral code from ?ref=XXX and store in session.
        Redirect to original page or shop.
        """
        ref = kwargs.get('ref')
        next_url = kwargs.get('next', '/shop')  # default redirect if no next
        if not next_url.startswith('/'):
            next_url = '/shop'

        if ref:
            # Persist referral code in session
            referral_set_at = int(time.time())
            request.session['referral_code'] = ref
            request.session['referral_code_set_at'] = referral_set_at
            partner = request.env['res.partner'].sudo().search(
                [('referral_code', '=', ref), ('is_referrer', '=', True)],
                limit=1
            )
            if partner:
                request.env['influencer.referral.visit.stat'].sudo().log_visit(partner)
                # Log individual visit with geolocation
                visitor_ip = InfluencerReferralVisitLog._get_visitor_ip(request)
                location = _lookup_location(visitor_ip)
                request.env['influencer.referral.visit.log'].sudo().create({
                    'partner_id': partner.id,
                    'visitor_ip': visitor_ip,
                    **location,
                })
            _logger.info("Referral code added to session: %s", ref)

            expiry_dt = datetime.utcnow() + timedelta(seconds=REFERRAL_SESSION_TTL_SECONDS)

            # Persist to partner DB (cross-device restore) when user is logged in
            if not request.env.user._is_public():
                request.env.user.partner_id.sudo().write({
                    'tracked_referral_code': ref,
                    'tracked_referral_code_expiry': expiry_dt,
                })

            # New users should signup first via our mobile signup which sets referred_by_id.
            if request.env.user._is_public():
                request.session['post_signup_redirect'] = next_url
                resp = request.redirect('/mobile/signup')
            else:
                resp = request.redirect(next_url)

            # Set long-lived browser cookie so the code survives new sessions / browsers
            resp.set_cookie(
                REFERRAL_COOKIE_NAME, ref,
                max_age=REFERRAL_SESSION_TTL_SECONDS,
                httponly=False,
                samesite='Lax',
            )
            resp.set_cookie(
                REFERRAL_COOKIE_SET_AT_NAME, str(referral_set_at),
                max_age=REFERRAL_SESSION_TTL_SECONDS,
                httponly=False,
                samesite='Lax',
            )
            return resp

        else:
            _logger.info("No referral code in URL.")

        # Redirect to the page user intended
        return request.redirect(next_url)


    # ----------------------------------------------------
    # BROWSER GPS LOCATION  /referral/location  (JSON-RPC POST)
    # ----------------------------------------------------

    @http.route('/referral/location', type='json', auth='public', website=True, methods=['POST'])
    def capture_referral_location(self, lat=None, lng=None, accuracy=None, **kw):
        """Receive browser GPS coordinates and attach them to the most recent
        visit log entry for the active referral session."""
        ref = request.session.get('referral_code')
        if not ref or lat is None or lng is None:
            return {'ok': False}

        partner = request.env['res.partner'].sudo().search([
            ('referral_code', '=', ref),
            ('is_referrer', '=', True),
        ], limit=1)
        if not partner:
            return {'ok': False}

        cutoff = datetime.utcnow() - timedelta(minutes=15)
        log = request.env['influencer.referral.visit.log'].sudo().search([
            ('partner_id', '=', partner.id),
            ('visit_datetime', '>=', cutoff),
        ], order='visit_datetime desc', limit=1)

        vals = {
            'gps_lat': float(lat),
            'gps_lng': float(lng),
            'gps_accuracy': float(accuracy or 0),
        }
        if log:
            log.write(vals)
        else:
            vals['partner_id'] = partner.id
            request.env['influencer.referral.visit.log'].sudo().create(vals)

        return {'ok': True}

    # ----------------------------------------------------
    # TOPLINE RECRUITING LINK  /influencer/recruit?tl=BLXTLXXXX
    # ----------------------------------------------------

    @http.route('/influencer/recruit', type='http', auth='public', website=True)
    def capture_topline_recruit(self, **kwargs):
        """
        Capture topline recruiting code from ?tl=BLXTLXXXX, store in session,
        and redirect to the influencer application form.
        Works for: link share, QR code, or manual URL entry.
        """
        tl = kwargs.get('tl', '').strip().upper()
        if tl:
            topline_partner = request.env['res.partner'].sudo().search([
                ('topline_referral_code', '=', tl),
                ('is_referrer', '=', True),
                ('influencer_state', '=', 'approved'),
                ('is_topline', '=', True),
            ], limit=1)
            if topline_partner:
                request.session['topline_recruit_code'] = tl
            else:
                # Invalid / unapproved — clear any stale session value
                request.session.pop('topline_recruit_code', None)

        # If not logged in → signup first, then come back to apply
        if request.env.user._is_public():
            request.session['post_signup_redirect'] = '/influencer/apply'
            return request.redirect('/mobile/signup?from_influencer=1')

        return request.redirect('/influencer/apply')


    # ----------------------------------------------------
    # PUBLIC LANDING PAGE
    # /influencer
    # # ----------------------------------------------------
  
    @http.route('/influencer', type='http', auth='public', website=True)
    def influencer_landing(self, **kw):
        return request.render(
            'qr_referral_points.influencer_landing_page'
        )
       
    
    def _get_available_delivery_towns(self):
        kenya = request.env['res.country'].sudo().search([('code', '=', 'KE')], limit=1)
        state_model = request.env['res.country.state'].sudo()
        if not kenya:
            return state_model.browse()
        return state_model.search([('country_id', '=', kenya.id)], order='name asc')

    @http.route('/influencer/apply', type='http', auth='public', website=True)
    def influencer_apply_form(self, **kw):
        # If not logged in → store redirect target and send to mobile OTP signup
        if request.env.user._is_public():
            request.session['post_signup_redirect'] = '/influencer/apply'
            _logger.info(
                'Unauthenticated user on /influencer/apply — '
                'storing post_signup_redirect and sending to /mobile/signup'
            )
            return request.redirect('/mobile/signup?from_influencer=1')

        partner = request.env.user.partner_id

        # Already applied → portal
        if partner.applied_as_influencer:
            return request.redirect('/my/influencer')

        countries = request.env['res.country'].sudo().search([], order='name')
        delivery_towns = self._get_available_delivery_towns()
        terms_html = request.env['influencer.program.config'].sudo().get_terms()

        # Pre-fill topline code from URL param (?tl=) or session (set by /influencer/recruit)
        prefill_topline_code = (
            kw.get('tl', '').strip().upper()
            or request.session.get('topline_recruit_code', '')
        )

        return request.render(
            'qr_referral_points.influencer_application_form',
            {
                'partner': partner,
                'countries': countries,
                'delivery_towns': delivery_towns,
                'terms_html': terms_html,
                'prefill_topline_code': prefill_topline_code,
            }
        )


    # ----------------------------------------------------
    # SUBMIT APPLICATION (POST)
    # /my/influencer/submit
    # ----------------------------------------------------
    @http.route(
        '/my/influencer/submit',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=True
    )
    def influencer_submit(self, **post):
        partner = request.env.user.partner_id

        # Prevent duplicate submissions
        if partner.applied_as_influencer:
            return request.redirect('/my/influencer')

        def _clean(val):
            return (val or '').strip() or False

        # Handle profile picture upload
        image_data = False
        image_file = post.get('image_1920')
        if image_file and hasattr(image_file, 'read'):
            content = image_file.read()
            if content:
                image_data = base64.b64encode(content)

        # Many2one IDs come as string integers from selects
        country_id_raw = post.get('country_id', '').strip()
        country_id = int(country_id_raw) if country_id_raw.isdigit() else False

        # If user signed up via referral link, persist the code to their profile now
        ref_in_session = request.session.get('referral_code', '')
        if ref_in_session and not partner.tracked_referral_code:
            partner.sudo().write({
                'tracked_referral_code': ref_in_session,
                'tracked_referral_code_expiry': datetime.utcnow() + timedelta(seconds=REFERRAL_SESSION_TTL_SECONDS),
            })

        vals = {
            'name': _clean(post.get('name')) or partner.name,
            'email': _clean(post.get('email')) or partner.email,
            'mobile': _clean(post.get('phone')) or partner.mobile,
            # Shared partner fields
            'id_number': _clean(post.get('id_number')),
            'birthdate': _clean(post.get('birthdate')) or False,
            'gender': _clean(post.get('gender')),
            'county': _clean(post.get('county')),
            'city': _clean(post.get('city')),           # delivery town → city
            'country_id': country_id,                  # nationality → country_id
            # Tax & payment
            'vat': _clean(post.get('vat')),
            'influencer_payment_account': _clean(post.get('influencer_payment_account')),
            # Influencer profile
            'influencer_join_reason': _clean(post.get('influencer_join_reason')),
            'influencer_experience_years': _clean(post.get('influencer_experience_years')),
            'influencer_referral_source': _clean(post.get('influencer_referral_source')),
            'influencer_tiktok_link': _clean(post.get('influencer_tiktok_link')),
            'influencer_construction_knowledge': _clean(post.get('influencer_construction_knowledge')),
            # Integrity
            'influencer_convicted': post.get('influencer_convicted') == '1',
            'influencer_conviction_details': _clean(post.get('influencer_conviction_details')),
            'influencer_terms_accepted': post.get('influencer_terms_accepted') == '1',
            # Communication modes (checkboxes: present = checked)
            'comm_mode_call': bool(post.get('comm_mode_call')),
            'comm_mode_whatsapp': bool(post.get('comm_mode_whatsapp')),
            'comm_mode_sms': bool(post.get('comm_mode_sms')),
            'applied_as_influencer': True,
            'influencer_state': 'review',
        }

        # Topline code: from form field, URL param, or session (set by /influencer/recruit link)
        topline_code = (
            _clean(post.get('topline_code'))
            or request.session.get('topline_recruit_code', '')
        )
        if topline_code and not partner.topline_id:
            topline_partner = request.env['res.partner'].sudo().search([
                ('topline_referral_code', '=', topline_code),
                ('is_referrer', '=', True),
                ('influencer_state', '=', 'approved'),
                ('is_topline', '=', True),
            ], limit=1)
            if topline_partner:
                vals['topline_id'] = topline_partner.id
        # Clear session topline code after use (one-time capture)
        request.session.pop('topline_recruit_code', None)

        vals.update({
            'influencer_facebook_link': _clean(post.get('facebook_link')),
            'influencer_instagram_link': _clean(post.get('instagram_link')),
            'influencer_x_link': _clean(post.get('x_link')),
            'influencer_linkedin_link': _clean(post.get('linkedin_link')),
            'influencer_youtube_link': _clean(post.get('youtube_link')),
        })
        if image_data:
            vals['image_1920'] = image_data

        partner.sudo().write(vals)

        # Notify internal users (appears in chatter)
        partner.message_post(
            body="New influencer application submitted via website."
        )

        return request.redirect('/my/influencer')
  



    @http.route('/my/influencer', type='http', auth='user', website=True)
    def influencer_portal(self, stage=None, **kw):
        partner = request.env.user.partner_id

        # ----------------------------------------------------
        # SECURITY CHECK
        # ----------------------------------------------------
        if not partner.is_referrer:
            return request.render(
                'qr_referral_points.referral_portal_template',
                {'partner': partner}
            )

        # ----------------------------------------------------
        # FETCH ORDERS & MONTHLY DATA
        # ----------------------------------------------------
        valid_stages = ('ordered', 'dispatched', 'invoiced', 'delivered', 'paid')
        # active_stage kept for initial CSS state only; orders are always all-stage
        # so the sales tab filters client-side without a page reload.
        active_stage = stage if stage in valid_stages else None

        SaleOrder = request.env['sale.order'].sudo()
        # Always fetch ALL orders – JS handles the stage filtering
        orders = SaleOrder.search([
            ('referral_partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ], order='create_date desc')

        monthly_data = defaultdict(lambda: {
            'orders': [],
            'order_count': 0,
            'total_amount': 0.0,
            'invoiced_amount': 0.0,
            'paid_invoiced_amount': 0.0,
        })

        # Status pipeline counts across all orders
        status_counts = {'ordered': 0, 'dispatched': 0, 'invoiced': 0, 'delivered': 0, 'paid': 0}

        for order in orders:
            month_key = order.create_date.strftime('%Y-%m')
            monthly_data[month_key]['orders'].append(order)
            monthly_data[month_key]['order_count'] += 1

            monthly_data[month_key]['total_amount'] = float_round(
                monthly_data[month_key]['total_amount'] + order.amount_total,
                precision_digits=2
            )

            posted_invoices = order.invoice_ids.filtered(lambda i: i.state == 'posted')
            paid_invoices = posted_invoices.filtered(lambda i: i.payment_state in ('paid', 'in_payment'))

            monthly_data[month_key]['invoiced_amount'] = float_round(
                monthly_data[month_key]['invoiced_amount'] + sum(posted_invoices.mapped('amount_total')),
                precision_digits=2
            )

            monthly_data[month_key]['paid_invoiced_amount'] = float_round(
                monthly_data[month_key]['paid_invoiced_amount'] + sum(paid_invoices.mapped('amount_total')),
                precision_digits=2
            )

            # Determine current pipeline step for this order
            step = self._get_order_pipeline_step(order)
            status_counts[step] += 1

        # ----------------------------------------------------
        # SALES PERFORMANCE METRICS (always from all orders, no stage filter)
        # ----------------------------------------------------
        all_orders_for_metrics = SaleOrder.search([
            ('referral_partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ])
        total_orders = len(all_orders_for_metrics)
        paid_orders_count = sum(
            1 for o in all_orders_for_metrics
            if self._get_order_pipeline_step(o) == 'paid'
        )
        conversion_rate = round(paid_orders_count / total_orders * 100, 1) if total_orders else 0.0
        avg_order_value = (
            round(sum(all_orders_for_metrics.mapped('amount_total')) / total_orders, 2)
            if total_orders else 0.0
        )
        customer_order_counts = defaultdict(int)
        for o in all_orders_for_metrics:
            customer_order_counts[o.partner_id.id] += 1
        unique_customers = len(customer_order_counts)
        repeat_customers = sum(1 for cnt in customer_order_counts.values() if cnt > 1)
        repeat_rate = round(repeat_customers / unique_customers * 100, 1) if unique_customers else 0.0

        sales_metrics = {
            'orders_closed': paid_orders_count,
            'conversion_rate': conversion_rate,
            'avg_order_value': avg_order_value,
            'repeat_rate': repeat_rate,
            'total_orders': total_orders,
            'unique_customers': unique_customers,
            'repeat_customers': repeat_customers,
        }

        # ----------------------------------------------------
        # AUTO-PAYOUT LOGIC
        # ----------------------------------------------------
        # plan = partner.commission_plan_id  # Assuming partner has a related plan
        # if plan and partner.wallet_balance >= plan.auto_payout_minimum:
        #     _logger.info("Triggering auto payout for partner %s", partner.name)

        #     # Create batch
        #     batch = request.env['influencer.commission.batch'].sudo().create({
        #         'name': f'Auto Payout - {partner.name}',
        #         'date_from': fields.Date.today(),
        #         'date_to': fields.Date.today(),
        #     })

        #     # Fetch eligible commissions
        #     commissions = request.env['influencer.commission'].sudo().search([
        #         ('partner_id', '=', partner.id),
        #         ('state', '=', 'approved'),
        #         ('batch_id', '=', False),
        #     ])

        #     # Assign to batch and update state
        #     commissions.sudo().write({
        #         'batch_id': batch.id,
        #         'state': 'batched'
        #     })

        #     # Create vendor bills automatically
        #     batch.sudo().action_create_vendor_bills()
        #     _logger.info("Auto payout batch %s created for partner %s", batch.name, partner.name)

        # # ----------------------------------------------------
        # # WALLET TRANSACTIONS
        # # ----------------------------------------------------
        # transactions = request.env['influencer.wallet.transaction'].sudo().search([
        #     ('partner_id', '=', partner.id)
        # ], order='create_date desc')

        # # ----------------------------------------------------
        # # RENDER PORTAL
        # # ----------------------------------------------------
        # return request.render(
        #     'qr_referral_points.referral_portal_template',
        #     {
        #         'partner': partner,
        #         'monthly_sales': monthly_data,
        #         'transactions': transactions,  # Add transactions for wallet tab
        #     }
        # )

        # ----------------------------------------------------
        # AUTO-PAYOUT LOGIC
        # ----------------------------------------------------
        plan = partner.commission_plan_id  # Assuming partner has a related plan
        if plan and plan.auto_payout_enabled and partner.wallet_balance >= plan.auto_payout_minimum:
            _logger.info("Triggering auto payout for partner %s", partner.name)

            # Create batch
            batch = request.env['influencer.commission.batch'].sudo().create({
                'name': f'Auto Payout - {partner.name}',
                'date_from': fields.Date.today(),
                'date_to': fields.Date.today(),
            })

            # Fetch eligible commissions
            commissions = request.env['influencer.commission'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'approved'),
                ('batch_id', '=', False),
            ])

            # Assign to batch and update state
            commissions.sudo().write({
                'batch_id': batch.id,
                'state': 'batched'
            })

            # Create vendor bills automatically
            batch.sudo().action_create_vendor_bills()
            _logger.info("Auto payout batch %s created for partner %s", batch.name, partner.name)

        # ----------------------------------------------------
        # WALLET TRANSACTIONS
        # ----------------------------------------------------
        transactions = request.env['influencer.wallet.transaction'].sudo().search([
            ('partner_id', '=', partner.id)
        ], order='create_date desc')

        unapproved_commissions = request.env['influencer.commission'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
        ])
        pending_commission_total = sum(unapproved_commissions.mapped('commission_amount'))

        # All commissions for this influencer
        all_commissions = request.env['influencer.commission'].sudo().search([
            ('partner_id', '=', partner.id),
        ])

        direct_commissions = all_commissions.filtered(lambda c: c.commission_type == 'direct')
        all_commissions_summary = {
            'gross': round(sum(direct_commissions.mapped('commission_amount')), 2),
            'topline_deduction': round(sum(direct_commissions.mapped('topline_deduction')), 2),
            'tax': round(sum(direct_commissions.mapped('tax_amount')), 2),
            'net': round(sum(direct_commissions.mapped('net_amount')), 2),
        }

        from datetime import date as _date
        _today = _date.today()
        _this_month = _today.strftime('%Y-%m')

        today_earned = sum(
            c.net_amount for c in all_commissions
            if c.commission_type == 'direct' and c.create_date and c.create_date.date() == _today
        )
        monthly_earned = sum(
            c.net_amount for c in all_commissions
            if c.commission_type == 'direct' and c.create_date and c.create_date.strftime('%Y-%m') == _this_month
        )
        paid_earned = sum(
            c.net_amount for c in all_commissions
            if c.state == 'paid'
        )
        total_tax_withheld = sum(all_commissions.mapped('tax_amount'))

        # Topline bonus commissions earned by this influencer
        topline_commissions = all_commissions.filtered(
            lambda c: c.commission_type == 'topline'
        ).sorted('create_date', reverse=True)
        topline_earned_total = sum(topline_commissions.mapped('commission_amount'))

        # All registered users who signed up via this influencer's referral link
        referred_users = request.env['res.partner'].sudo().search([
            ('referred_by_id', '=', partner.id),
        ], order='create_date desc')

        # Referral network: anyone this partner recruited (any approval state)
        network_partners = request.env['res.partner'].sudo().search([
            ('topline_id', '=', partner.id),
            ('applied_as_influencer', '=', True),
        ])

        # Turnover per referred influencer (total confirmed sale value)
        network_turnover = {}
        for np in network_partners:
            np_orders = request.env['sale.order'].sudo().search([
                ('referral_partner_id', '=', np.id),
                ('state', 'in', ['sale', 'done']),
            ])
            network_turnover[np.id] = round(sum(np_orders.mapped('amount_total')), 2)

        # Payout batches for this partner (any commission in batch belongs to partner)
        payout_batches = request.env['influencer.commission.batch'].sudo().search([
            ('commission_ids.partner_id', '=', partner.id),
        ], order='create_date desc')

        # Attach related vendor bill to each batch for display
        payout_history = []
        for batch in payout_batches:
            bill = request.env['account.move'].sudo().search([
                ('move_type', '=', 'in_invoice'),
                ('partner_id', '=', partner.id),
                ('invoice_line_ids.name', 'like', batch.name),
            ], limit=1)
            batch_commissions = batch.commission_ids.filtered(lambda c: c.partner_id == partner)
            payout_history.append({
                'batch': batch,
                'total': sum(batch_commissions.mapped('commission_amount')),
                'bill': bill,
                'bill_state': bill.payment_state if bill else False,
            })

        visit_stats = request.env['influencer.referral.visit.stat'].sudo().search([
            ('partner_id', '=', partner.id)
        ], order='date desc', limit=30)
        visit_logs = request.env['influencer.referral.visit.log'].sudo().search([
            ('partner_id', '=', partner.id)
        ], order='visit_datetime desc', limit=100)

        # ----------------------------------------------------
        # RENDER PORTAL
        # ----------------------------------------------------
        return request.render(
            'qr_referral_points.referral_portal_template',
            {
                'partner': partner,
                'monthly_sales': monthly_data,
                'transactions': transactions,
                'visit_stats': visit_stats,
                'visit_logs': visit_logs,
                'status_counts': status_counts,
                'active_stage': active_stage,
                'pending_commission_total': pending_commission_total,
                'payout_history': payout_history,
                'all_commissions_summary': all_commissions_summary,
                'topline_commissions': topline_commissions,
                'topline_earned_total': topline_earned_total,
                'today_earned': today_earned,
                'monthly_earned': monthly_earned,
                'paid_earned': paid_earned,
                'total_tax_withheld': total_tax_withheld,
                'network_partners': network_partners,
                'network_turnover': network_turnover,
                'referred_users': referred_users,
                'sales_metrics': sales_metrics,
                'recruit_base_url': request.httprequest.host_url.rstrip('/'),
            }
        )

    def _get_order_pipeline_step(self, order):
        """Return the pipeline stage for a sale order (aligned with influencer_order_stage field).

        Stages:
          paid       – invoice paid / in_payment
          delivered  – posted (confirmed) invoice, not yet paid
          invoiced   – draft invoice exists
          dispatched – delivery validated (picking done), no invoice yet
          ordered    – confirmed order, nothing else yet
        """
        invoices = order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
        paid_inv = invoices.filtered(lambda m: m.payment_state in ('paid', 'in_payment'))
        posted_inv = invoices.filtered(lambda m: m.state == 'posted')
        draft_inv = invoices.filtered(lambda m: m.state == 'draft')
        if paid_inv:
            return 'paid'
        if posted_inv:
            return 'invoiced'
        if draft_inv:
            return 'delivered'
        if order.picking_ids.filtered(lambda p: p.state == 'done'):
            return 'dispatched'
        return 'ordered'




    @http.route('/my/influencer/request_payout', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def influencer_request_payout(self, **post):
        partner = request.env.user.partner_id
        plan = partner.commission_plan_id

        # Check if minimum balance is reached
        if not plan or partner.wallet_balance < plan.auto_payout_minimum:
            return request.redirect('/my/influencer')

        # Create batch
        batch = request.env['influencer.commission.batch'].sudo().create({
            'name': f'Manual Payout Request - {partner.name}',
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })

        # Fetch eligible commissions
        commissions = request.env['influencer.commission'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'approved'),
            ('batch_id', '=', False),
        ])

        # Assign to batch and update state
        commissions.sudo().write({
            'batch_id': batch.id,
            'state': 'batched'
        })

        # Create vendor bills automatically
        batch.sudo().action_create_vendor_bills()

        return request.redirect('/my/influencer')
