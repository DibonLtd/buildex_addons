import json

from odoo.addons.website.controllers.form import WebsiteForm
from odoo.http import request


class BuildexWebsiteForm(WebsiteForm):

    def _is_buildex_contact_sales_submission(self, model_name):
        if model_name not in ('mail.mail', 'crm.lead'):
            return False
        referer = request.httprequest.headers.environ.get('HTTP_REFERER', '') or ''
        return '/contactus' in referer

    def _buildex_sync_contact_sales_item(self, model_name, kwargs):
        if not request.env.registry.get('buildex.fundi.request'):
            return False

        Partner = request.env['res.partner'].sudo()
        email = (kwargs.get('email_from') or kwargs.get('email') or '').strip()
        phone = (kwargs.get('phone') or kwargs.get('mobile') or '').strip()
        name = (kwargs.get('contact_name') or kwargs.get('name') or '').strip()
        company = (kwargs.get('partner_name') or kwargs.get('company_name') or kwargs.get('company') or '').strip()
        subject = (kwargs.get('subject') or kwargs.get('name') or 'Sales Inquiry').strip()
        description = (kwargs.get('description') or '').strip()

        partner = False
        if email:
            partner = Partner.search([('email', '=', email)], limit=1)
        if not partner and phone:
            partner = Partner.search([('phone', '=', phone)], limit=1)
        if not partner and (name or phone or email):
            partner = Partner.create({
                'name': name or company or phone or email or 'Website Sales Inquiry',
                'phone': phone,
                'email': email,
                'company_name': company,
            })

        note_parts = [part for part in [subject, description] if part]
        if company:
            note_parts.insert(0, f'Company: {company}')

        request.env['buildex.fundi.request'].sudo().with_context(
            tracking_disable=True,
            mail_create_nosubscribe=True,
        ).create({
            'source': 'contact_sales_form',
            'request_type': 'sales_inquiry',
            'partner_id': partner.id if partner else False,
            'requested_by_name': name or (partner.name if partner else False) or company or 'Website Customer',
            'phone': phone or (partner.phone if partner else False),
            'email': email or (partner.email if partner else False),
            'requested_service': 'Contact Sales Inquiry',
            'note': '\n'.join(note_parts),
            'internal_note': (
                f'Actionable sales request captured from website contact form ({model_name}).'
            ),
            'priority': '2',
            'action_point': 'sales_callback',
        })

    def _handle_website_form(self, model_name, **kwargs):
        response = super()._handle_website_form(model_name, **kwargs)
        if self._is_buildex_contact_sales_submission(model_name):
            try:
                payload = json.loads(response)
            except Exception:
                payload = {}
            if payload and not payload.get('error'):
                self._buildex_sync_contact_sales_item(model_name, kwargs)
        return response
