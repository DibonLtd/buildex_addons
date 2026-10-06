from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, route


class WebsiteSaleCheckoutKE(WebsiteSale):

    def _get_kenya_country(self):
        return request.env['res.country'].sudo().search([('code', '=', 'KE')], limit=1)

    def _get_allowed_states(self, country):
        country = country.sudo()
        if country.code == 'KE':
            return country.state_ids.filtered('is_delivery_town')
        return country.state_ids

    def _is_confirm_only_checkout(self, order_sudo):
        partner = order_sudo.partner_id.commercial_partner_id
        return partner.checkout_payment_policy == 'confirm_only'

    def _get_contact_group_categories(self):
        env = request.env
        return {
            'b2c': env.ref('website_sale_checkout_ke.partner_category_b2c', raise_if_not_found=False),
            'b2b': env.ref('website_sale_checkout_ke.partner_category_b2b', raise_if_not_found=False),
            'fundi': env.ref('website_sale_checkout_ke.partner_category_fundi', raise_if_not_found=False),
        }

    def _get_buildex_fundi_request_model(self):
        return request.env.registry.get('buildex.fundi.request')

    def _sync_buildex_fundi_request(self, source, order_sudo=None, partner=None, product=None, payload=None):
        if not self._get_buildex_fundi_request_model():
            return False

        payload = payload or {}
        partner = partner or (order_sudo.partner_id.commercial_partner_id if order_sudo else request.env['res.partner'])
        FundiRequest = request.env['buildex.fundi.request'].sudo().with_context(
            tracking_disable=True,
            mail_create_nosubscribe=True,
        )
        product_variant = product.product_variant_id if getattr(product, 'product_variant_id', False) else product

        vals = {
            'source': source,
            'request_type': payload.get('request_type') or 'fundi_support',
            'partner_id': partner.id if partner else False,
            'sale_order_id': order_sudo.id if order_sudo else False,
            'product_id': product_variant.id if product_variant else False,
            'requested_by_name': payload.get('requested_by_name') or (partner.name if partner else False),
            'phone': payload.get('phone') or (partner.phone if partner else False),
            'email': payload.get('email') or (partner.email if partner else False),
            'city': payload.get('city') or (partner.city if partner else False),
            'requested_service': payload.get('requested_service') or 'Fundi / Technician Support',
            'note': payload.get('note'),
            'internal_note': payload.get('internal_note'),
            'assigned_user_id': payload.get('assigned_user_id') or (order_sudo.user_id.id if order_sudo and order_sudo.user_id else False),
            'priority': payload.get('priority') or '2',
            'action_point': payload.get('action_point') or 'call_customer',
        }
        vals = {key: value for key, value in vals.items() if value not in (False, None, '')}

        if source == 'checkout_post_payment' and order_sudo:
            existing = FundiRequest.search([
                ('sale_order_id', '=', order_sudo.id),
                ('source', '=', source),
                ('state', 'not in', ('completed', 'cancelled')),
            ], limit=1, order='id desc')
            if existing:
                existing.write(vals)
                return existing

        return FundiRequest.create(vals)

    def _prepare_address_form_values(
        self, order_sudo, partner_sudo, address_type, use_delivery_as_billing, callback='', **kwargs
    ):
        values = super()._prepare_address_form_values(
            order_sudo,
            partner_sudo,
            address_type,
            use_delivery_as_billing,
            callback=callback,
            **kwargs,
        )

        country = values.get('country') or self._get_kenya_country()
        if country:
            values['country'] = country
            allowed_states = self._get_allowed_states(country)
            values['country_states'] = allowed_states
            if values.get('state_id') and values['state_id'] not in allowed_states.ids:
                values['state_id'] = False

        return values

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        required = {'phone'}
        if country_sudo and (country_sudo.code == 'KE' or country_sudo.state_required):
            required.add('state_id')
        return required

    def _get_mandatory_billing_address_fields(self, country_sudo):
        required = {'phone'}
        if country_sudo and (country_sudo.code == 'KE' or country_sudo.state_required):
            required.add('state_id')
        return required

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)

        if not address_values.get('country_id'):
            kenya = self._get_kenya_country()
            if kenya:
                address_values['country_id'] = kenya.id

        # Odoo partner creation needs a name; keep it auto-filled if customer leaves it blank.
        if not address_values.get('name'):
            address_values['name'] = (
                address_values.get('company_name')
                or address_values.get('phone')
                or 'Website Customer'
            )

        country = request.env['res.country'].sudo().browse(address_values.get('country_id'))
        state_id = address_values.get('state_id')
        if country and country.code == 'KE' and state_id:
            state = request.env['res.country.state'].sudo().browse(state_id)
            if state and not state.is_delivery_town:
                address_values['state_id'] = False

        return address_values, extra_form_data

    @route(
        ['/shop/country_info/<model("res.country"):country>'],
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def shop_country_info(self, country, address_type, **kw):
        data = super().shop_country_info(country, address_type, **kw)
        allowed_states = self._get_allowed_states(country)
        data['states'] = [(st.id, st.name, st.code) for st in allowed_states]
        return data

    @route(['/shop/confirm_order'], type='http', auth='public', website=True, sitemap=False)
    def shop_confirm_order(self, **post):
        order_sudo = request.website.sale_get_order()

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        order_sudo._recompute_taxes()
        order_sudo._recompute_prices()
        extra_step = request.website.viewref('website_sale.extra_info')
        if extra_step.active:
            return request.redirect('/shop/extra_info')

        if self._is_confirm_only_checkout(order_sudo):
            if order_sudo.state != 'sale':
                order_sudo._check_cart_is_ready_to_be_paid()
                order_sudo._validate_order()
            request.session['sale_last_order_id'] = order_sudo.id
            request.website.sale_reset()
            return request.redirect('/shop/confirmation')

        # Redirect to payment preference step before payment
        return request.redirect('/shop/payment_preference')

    def _check_shipping_method(self, order_sudo):
        """Skip the shipping method check that redirects to /shop/checkout.

        The custom KE checkout flow does not include a shipping method selection
        step, so the delivery-ready check would always fail and loop back to
        /shop/checkout.  Return None to let the payment page render normally.
        """
        return None

    @route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        order_sudo = request.website.sale_get_order()
        if order_sudo and self._is_confirm_only_checkout(order_sudo):
            return request.redirect('/shop/confirm_order')
        return super().shop_payment(**post)

    # ------------------------------------------------------------------
    # PAYMENT PREFERENCE STEP
    # ------------------------------------------------------------------

    @route('/shop/payment_preference', type='http', auth='public', website=True, sitemap=False)
    def shop_payment_preference(self, **post):
        """Show Pay Now / Pay After Delivery choice."""
        order_sudo = request.website.sale_get_order()
        if not order_sudo:
            return request.redirect('/shop')

        if request.httprequest.method == 'POST':
            preference = post.get('payment_preference', 'pay_now')
            order_sudo.sudo().write({'payment_preference': preference})

            if preference == 'pay_after_delivery':
                # Place order now (payment collected on delivery)
                if order_sudo.state != 'sale':
                    order_sudo.sudo()._check_cart_is_ready_to_be_paid()
                    order_sudo.sudo()._validate_order()
                request.session['sale_last_order_id'] = order_sudo.id
                request.website.sale_reset()
                return request.redirect('/shop/post_payment')

            # pay_now → go to payment; technician question asked after payment
            return request.redirect('/shop/payment')

        return request.render(
            'website_sale_checkout_ke.payment_preference_template',
            {'order': order_sudo},
        )

    @route(['/shop/payment/transaction/<int:provider_id>'], type='json', auth='public', website=True)
    def shop_payment_transaction(self, provider_id, **kwargs):
        """Force landing_route to post_payment so /payment/status is skipped."""
        kwargs['landing_route'] = '/shop/post_payment'
        return super().shop_payment_transaction(provider_id, **kwargs)

    # ------------------------------------------------------------------
    # POST-PAYMENT TECHNICIAN QUESTION
    # ------------------------------------------------------------------

    @route('/shop/post_payment', type='http', auth='public', website=True, sitemap=False)
    def shop_post_payment(self, **post):
        """Ask technician Yes/No after payment/order placement."""
        order_sudo = request.env['sale.order'].sudo().browse(
            request.session.get('sale_last_order_id')
        )
        if not order_sudo.exists():
            return request.redirect('/shop')

        if request.httprequest.method == 'POST':
            wants_technician = post.get('wants_technician', 'no') == 'yes'
            if wants_technician:
                self._sync_buildex_fundi_request(
                    'checkout_post_payment',
                    order_sudo=order_sudo,
                    partner=order_sudo.partner_id.commercial_partner_id,
                    payload={
                        'requested_by_name': order_sudo.partner_id.name,
                        'phone': order_sudo.partner_id.phone,
                        'email': order_sudo.partner_id.email,
                        'city': order_sudo.partner_shipping_id.city or order_sudo.partner_id.city,
                        'requested_service': 'Website checkout technician request',
                        'note': 'Customer requested technician support after checkout.',
                        'internal_note': 'Respond to technician request from website checkout.',
                        'action_point': 'call_customer',
                        'priority': '3',
                    },
                )
                request.session['ke_wants_technician'] = True
                return request.redirect('/shop/technician_info')
            return request.redirect('/shop/confirmation')

        return request.render(
            'website_sale_checkout_ke.post_payment_template',
            {'order': order_sudo},
        )

    # ------------------------------------------------------------------
    # TECHNICIAN INFO STEP
    # ------------------------------------------------------------------

    @route('/shop/technician_info', type='http', auth='public', website=True, sitemap=False)
    def shop_technician_info(self, **post):
        """Collect installation technician information (reached only when user said Yes)."""
        order_sudo = (
            request.website.sale_get_order()
            or request.env['sale.order'].sudo().browse(
                request.session.get('sale_last_order_id')
            )
        )
        if not order_sudo or not order_sudo.exists():
            return request.redirect('/shop')

        if request.httprequest.method == 'POST':
            vals = {}
            name = post.get('technician_name', '').strip()
            contact = post.get('technician_contact', '').strip()
            location = post.get('technician_location', '').strip()
            specs = post.get('technician_specs', '').strip()
            if name:
                vals['technician_name'] = name
            if contact:
                vals['technician_contact'] = contact
            if location:
                vals['technician_location'] = location
            if specs:
                vals['technician_specs'] = specs
            if vals:
                order_sudo.sudo().with_context(
                    mail_notrack=True,
                    mail_auto_subscribe_no_notify=True,
                ).write(vals)

            # Create or update a res.partner record for the fundi
            if name or contact:
                Partner = request.env['res.partner'].sudo()
                # Try to find existing fundi by phone contact
                fundi = contact and Partner.search(
                    [('is_fundi', '=', True), ('phone', '=', contact)], limit=1
                )
                partner_vals = {'is_fundi': True}
                if name:
                    partner_vals['name'] = name
                if contact:
                    partner_vals['phone'] = contact
                if location:
                    partner_vals['city'] = location
                if specs:
                    partner_vals['comment'] = specs
                if fundi:
                    fundi.write(partner_vals)
                else:
                    partner_vals.setdefault('name', contact or 'Fundi')
                    Partner.with_context(
                        mail_notrack=True,
                        mail_auto_subscribe_no_notify=True,
                    ).create(partner_vals)

            self._sync_buildex_fundi_request(
                'checkout_post_payment',
                order_sudo=order_sudo,
                partner=order_sudo.partner_id.commercial_partner_id,
                payload={
                    'requested_by_name': order_sudo.partner_id.name,
                    'phone': order_sudo.partner_id.phone or contact,
                    'email': order_sudo.partner_id.email,
                    'city': location or order_sudo.partner_shipping_id.city or order_sudo.partner_id.city,
                    'requested_service': 'Website checkout technician request',
                    'note': specs or 'Customer requested technician support from checkout flow.',
                    'internal_note': 'Contact customer and assign a fundi if needed.',
                    'action_point': 'assign_nearest_fundi' if name or contact else 'call_customer',
                    'priority': '3',
                },
            )

            # Mark technician step done so confirmation doesn't loop back
            request.session.pop('ke_wants_technician', None)
            return request.redirect('/shop/confirmation')

        return request.render(
            'website_sale_checkout_ke.technician_info_template',
            {'order': order_sudo},
        )

    # ------------------------------------------------------------------
    # ORDER CONFIRMATION — "Awaiting Confirmation"
    # ------------------------------------------------------------------

    @route('/shop/confirmation', type='http', auth='public', website=True, sitemap=False)
    def shop_confirmation(self, **post):
        """Show 'Awaiting Confirmation' page."""
        request.session.pop('ke_wants_technician', None)
        order_sudo = request.env['sale.order'].sudo().browse(
            request.session.get('sale_last_order_id')
        )
        if not order_sudo.exists():
            return request.redirect('/shop')

        return request.render(
            'website_sale_checkout_ke.order_awaiting_confirmation',
            {'order': order_sudo},
        )

    @route('/fundi-request', type='http', auth='public', website=True, sitemap=True)
    def fundi_request(self, **post):
        """Website form for manual technician/Fundi requests."""
        product = False
        product_id = post.get('product_id')
        if product_id and str(product_id).isdigit():
            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists():
                product = False

        values = {
            'submitted': False,
            'product': product,
            'defaults': {
                'name': post.get('name', ''),
                'phone': post.get('phone', ''),
                'email': post.get('email', ''),
                'company_name': post.get('company_name', ''),
                'city': post.get('city', ''),
                'message': post.get('message', ''),
                'group_b2c': post.get('group_b2c'),
                'group_b2b': post.get('group_b2b'),
                'group_fundi': post.get('group_fundi'),
            },
        }

        if request.httprequest.method == 'POST':
            Partner = request.env['res.partner'].sudo()
            categories = self._get_contact_group_categories()

            email = (post.get('email') or '').strip()
            phone = (post.get('phone') or '').strip()
            name = (post.get('name') or '').strip()
            company_name = (post.get('company_name') or '').strip()
            city = (post.get('city') or '').strip()
            message = (post.get('message') or '').strip()

            partner = False
            if email:
                partner = Partner.search([('email', '=', email)], limit=1)
            if not partner and phone:
                partner = Partner.search([('phone', '=', phone)], limit=1)

            selected_category_ids = []
            if post.get('group_b2c') and categories['b2c']:
                selected_category_ids.append(categories['b2c'].id)
            if post.get('group_b2b') and categories['b2b']:
                selected_category_ids.append(categories['b2b'].id)
            if post.get('group_fundi') and categories['fundi']:
                selected_category_ids.append(categories['fundi'].id)

            note_parts = []
            if company_name:
                note_parts.append('Company / Shop: %s' % company_name)
            if message:
                note_parts.append(message)
            if product:
                note_parts.append('Requested from website product: %s' % product.name)

            partner_vals = {
                'name': name or phone or email or 'Website Fundi Request',
                'phone': phone,
                'email': email,
                'city': city,
                'comment': '\n'.join(note_parts),
                'is_fundi': bool(post.get('group_fundi')),
            }
            if selected_category_ids:
                partner_vals['category_id'] = [(4, category_id) for category_id in selected_category_ids]

            if partner:
                partner.write(partner_vals)
            else:
                partner = Partner.create(partner_vals)

            self._sync_buildex_fundi_request(
                'website_form',
                partner=partner.commercial_partner_id if partner else False,
                product=product,
                payload={
                    'requested_by_name': name or company_name,
                    'phone': phone,
                    'email': email,
                    'city': city,
                    'requested_service': 'Website fundi request form',
                    'note': '\n'.join(note_parts),
                    'internal_note': 'New website fundi request awaiting customer service response.',
                    'action_point': 'call_customer',
                    'priority': '2',
                },
            )

            values['submitted'] = True

        return request.render('website_sale_checkout_ke.fundi_request_template', values)
