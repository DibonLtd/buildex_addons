# -*- coding: utf-8 -*-
from uuid import uuid4

from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.survey.controllers.main import Survey
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PortalSurvey(Survey):
    def _get_access_data(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        res = super()._get_access_data(survey_token, answer_token, ensure_token, check_partner)
        res['validity_code'] = True
        return res


class AppraisalsPortal(CustomerPortal):
    def _appraisals_domain(self):
        # Get the stage ids for 'Sent Mail' and 'Done' stages
        try:
            sent_mail_stage = request.env['hr.appraisal.stages'].search([('name', '=', 'Sent Mail')], limit=1)
            done_stage = request.env['hr.appraisal.stages'].search([('name', '=', 'Done')], limit=1)
            stage_ids = [s.id for s in [sent_mail_stage, done_stage] if s]
        except KeyError:
            # If hr.appraisal.stages model doesn't exist, return empty list
            stage_ids = []
        
        if stage_ids:
            return [
                ('employee_id', '!=', False),
                ('employee_id.user_partner_id', '=', request.env.user.partner_id.id),
                ('appraisal_state', 'in', stage_ids)
            ]
        else:
            # Fallback: return a domain that won't match anything if stages not found
            return [
                ('employee_id', '!=', False),
                ('employee_id.user_partner_id', '=', request.env.user.partner_id.id),
                ('id', '=', -1)
            ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'appraisal_count' in counters:
            appraisal_model = request.env['hr.appraisal']
            values['appraisal_count'] = appraisal_model.search_count(self._appraisals_domain()) or 0
        return values

    def _appraisal_get_page_view_values(self, appraisal, access_token, **kwargs):
        # if not appraisal.access_token:
        #     appraisal.access_token = uuid4().hex
        user = request.env.user
        user_inputs = request.env['survey.user_input'].search([('appraisal_id', '=', appraisal.id)])
        user_inputs = user_inputs.filtered(lambda u: u.partner_id == user.partner_id or u.state == 'done' )

        values = {
            'page_name': 'appraisal',
            'appraisal': appraisal,
            'user_inputs': user_inputs
        }
        return self._get_page_view_values(appraisal, access_token, values, 'my_appraisals_history', False, **kwargs)

    @http.route(['/my/appraisals', '/my/appraisals/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appraisals(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        appraisal_model = request.env['hr.appraisal']

        domain = self._appraisals_domain()

        searchbar_sortings = {
            'date_close': {'label': _('Appraisal Date'), 'order': 'date_close desc'},
            'employee_id': {'label': _('Name'), 'order': 'employee_id desc'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date_close'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date_close', '>=', date_begin), ('date_close', '<=', date_end)]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        appraisal_count = appraisal_model.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/appraisals",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=appraisal_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager and archive selected
        appraisals = appraisal_model.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_appraisals_history'] = appraisals.ids[:100]

        values.update({
            'date': date_begin,
            'appraisals': appraisals,
            'page_name': 'appraisal',
            'pager': pager,
            'default_url': '/my/appraisals',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby
        })
        return request.render("oo_portal_employees.portal_my_appraisals", values)

    @http.route(['/my/appraisals/<int:appraisal_id>'], type='http', auth="user", website=True)
    def portal_my_appraisal_details(self, appraisal_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            appraisal_sudo = self._document_check_access('hr.appraisal', appraisal_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._appraisal_get_page_view_values(appraisal_sudo, access_token, **kw)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=appraisal_sudo,
                                     report_type=report_type,
                                     report_ref='hr_payroll.action_report_payslip',
                                     download=download)
        return request.render("oo_portal_employees.portal_appraisal_page", values)

class TeamAppraisalsPortal(CustomerPortal):
    def _team_appraisals_domain(self):
        """Return domain to fetch appraisals for current user's team"""
        try:
            # Get the stage ids for 'Sent Mail' and 'Done' stages
            sent_mail_stage = request.env['hr.appraisal.stages'].search([('name', '=', 'Sent Mail')], limit=1)
            done_stage = request.env['hr.appraisal.stages'].search([('name', '=', 'Done')], limit=1)
            stage_ids = [s.id for s in [sent_mail_stage, done_stage] if s]
        except (KeyError, AttributeError):
            # If hr.appraisal.stages model doesn't exist, return empty domain
            stage_ids = []
        
        user = request.env.user
        # Guard: must have employee record
        if not user.employee_id or not stage_ids:
            return [('id', '=', -1)]  # Return no results safely
        
        employee_ids = user.employee_id.ids
        # Build domain: appraisals where user is manager, colleague, or collaborator AND in correct stage
        return [
            '&',
            ('appraisal_state', 'in', stage_ids),
            '|',
            '|',
            ('manager_ids', 'in', employee_ids),
            ('hr_colleague_id', 'in', employee_ids),
            ('hr_colloborator_id', 'in', employee_ids),
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'team_appraisal_count' in counters:
            appraisal_model = request.env['hr.appraisal']
            values['team_appraisal_count'] = appraisal_model.search_count(self._team_appraisals_domain()) or 0
        return values

    def _appraisal_get_page_view_values(self, appraisal, access_token, **kwargs):
        # if not appraisal.access_token:
        #     appraisal.access_token = uuid4().hex
        user = request.env.user
        user_inputs = request.env['survey.user_input'].search([('appraisal_id', '=', appraisal.id)])
        user_inputs = user_inputs.filtered(lambda u: u.partner_id == user.partner_id or u.state == 'done' )

        values = {
            'page_name': 'team_appraisal',
            'appraisal': appraisal,
            'user_inputs': user_inputs
        }
        return self._get_page_view_values(appraisal, access_token, values, 'my_team_appraisals_history', False, **kwargs)

    @http.route(['/my/team/appraisals', '/my/team/appraisals/page/<int:page>'], type='http', auth="user", website=True)
    def portal_team_appraisals(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        appraisal_model = request.env['hr.appraisal']

        domain = self._team_appraisals_domain()

        searchbar_sortings = {
            'date_close': {'label': _('Appraisal Date'), 'order': 'date_close desc'},
            'employee_id': {'label': _('Name'), 'order': 'employee_id desc'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date_close'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date_close', '>=', date_begin), ('date_close', '<=', date_end)]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        team_appraisal_count = appraisal_model.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/team/appraisals",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=team_appraisal_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager and archive selected
        team_appraisals = appraisal_model.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_team_appraisals_history'] = team_appraisals.ids[:100]

        values.update({
            'date': date_begin,
            'appraisals': team_appraisals,
            'page_name': 'team_appraisal',
            'pager': pager,
            'default_url': '/my/team/appraisals',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby
        })
        return request.render("oo_portal_employees.portal_my_appraisals", values)

    @http.route(['/my/team/appraisals/<int:appraisal_id>'], type='http', auth="user", website=True)
    def portal_team_appraisal_details(self, appraisal_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            appraisal_sudo = self._document_check_access('hr.appraisal', appraisal_id, access_token)
        except (AccessError, MissingError):
            # appraisal_sudo = request.env['hr.appraisal'].with_user(2).browse(appraisal_id)
            return request.redirect('/my')

        values = self._appraisal_get_page_view_values(appraisal_sudo, access_token, **kw)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=appraisal_sudo,
                                     report_type=report_type,
                                     report_ref='hr_payroll.action_report_payslip',
                                     download=download)
        return request.render("oo_portal_employees.portal_appraisal_page", values)
