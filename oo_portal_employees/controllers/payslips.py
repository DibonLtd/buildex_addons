# -*- coding: utf-8 -*-
from uuid import uuid4

from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class PayslipsPortal(CustomerPortal):
    def _payslips_domain(self):
        return [
            ('employee_id', '!=', False),
            ('employee_id.user_partner_id', '=', request.env.user.partner_id.id),
            ('state', 'in', ['done', 'paid'])
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'payslip_count' in counters:
            payslip_model = request.env['hr.payslip']
            values['payslip_count'] = payslip_model.search_count(self._payslips_domain()) or '0'
        return values

    def _payslip_get_page_view_values(self, payslip, access_token, **kwargs):
        if not payslip.access_token:
            payslip.access_token = uuid4().hex
        values = {
            'page_name': 'payslip',
            'payslip': payslip,
        }
        return self._get_page_view_values(payslip, access_token, values, 'my_payslips_history', False, **kwargs)

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_payslips(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        payslip_model = request.env['hr.payslip']

        domain = self._payslips_domain()

        searchbar_sortings = {
            'date_from': {'label': _('Date'), 'order': 'date_from desc'},
            'number': {'label': _('Slip Number'), 'order': 'number desc'},
        }
        # default sort by order
        if not sortby:
            sortby = 'number'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date_from', '>', date_begin), ('date_to', '<=', date_end)]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        payslip_count = payslip_model.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/payslips",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=payslip_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager and archive selected
        payslips = payslip_model.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_payslips_history'] = payslips.ids[:100]

        values.update({
            'date': date_begin,
            'payslips': payslips,
            'page_name': 'payslip',
            'pager': pager,
            'default_url': '/my/payslips',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby
        })
        return request.render("oo_portal_employees.portal_my_payslips", values)

    @http.route(['/my/payslips/<int:payslip_id>'], type='http', auth="user", website=True)
    def portal_my_payslip_details(self, payslip_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            payslip_sudo = self._document_check_access('hr.payslip', payslip_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._payslip_get_page_view_values(payslip_sudo, access_token, **kw)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=payslip_sudo,
                                     report_type=report_type,
                                     report_ref='hr_payroll.action_report_payslip',
                                     download=download)
        return request.render("oo_portal_employees.portal_payslip_page", values)
