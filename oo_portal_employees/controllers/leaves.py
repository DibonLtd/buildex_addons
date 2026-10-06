# -*- coding: utf-8 -*-
import logging
from uuid import uuid4
import base64
from datetime import timedelta, datetime

from dateutil.parser import parse
from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class LeavesPortal(CustomerPortal):

    # def _leaves_domain(self):
    #     return [('employee_id', '!=', False), ('employee_id.user_partner_id', '=', request.env.user.partner_id.id)]

    def _leaves_domain(self):
        current_user = request.env.user
        # Get employee for current user
        employee = request.env['hr.employee'].with_user(2).search([('user_partner_id', '=', current_user.partner_id.id)], limit=1)
        
        # Check if the current user is a leave approver/manager
        is_leave_manager = current_user.id in [2, 8, 14]
        
        if is_leave_manager:
            # Leave managers can see leaves to approve AND their own leaves
            if employee:
                return [
                    '|',
                    ('state', 'in', ['confirm', 'refuse', 'validate']),
                    ('employee_id', '=', employee.id)
                ]
            else:
                # Manager with no employee record sees all leaves to approve
                return [('employee_id', '!=', False), ('state', 'in', ['confirm', 'refuse', 'validate'])]
        elif employee:
            # Regular employees see only their own leaves
            return [('employee_id', '=', employee.id)]
        else:
            # No employee record, return empty domain
            return [('id', '=', -1)]
            
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'leave_count' in counters:
            leaves_model = request.env['hr.leave'].with_user(2)
            values['leave_count'] = leaves_model.search_count(self._leaves_domain()) or 0
        return values

    def _leaves_get_page_view_values(self, leave, access_token, **kwargs):
        if not leave.access_token:
            leave.access_token = uuid4().hex
        
        # Check permissions for CURRENT logged-in user, not admin
        current_user = request.env.user
        portal_leave_manager = current_user.has_group('oo_portal_employees.group_portal_employee_leave_manager')
        backend_leave_manager = current_user.has_group('hr_holidays.group_hr_holidays_responsible')
        
        values = {
            'page_name': 'leave',
            'leave': leave,
            'leave_types': request.env['hr.leave.type'].search([]),
            'is_readonly': bool(leave),
            'can_approve': (portal_leave_manager or backend_leave_manager) and leave.state not in ['draft', 'refuse', 'validate'],
            'can_refuse': (portal_leave_manager or backend_leave_manager) and leave.state not in ['draft', 'refuse'],
            'can_cancel': portal_leave_manager or backend_leave_manager,
        }
        # Get base page values and merge with leave-specific values
        page_values = self._get_page_view_values(leave, access_token, values, 'my_leaves_history', False, **kwargs)
        # Ensure leave is in the final values
        page_values['leave'] = leave
        return page_values
    
    def _check_access_rights(self, leave_id, access_token):
        try:
            leave_sudo = self._document_check_access('hr.leave', leave_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return leave_sudo

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leaves(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        leaves_model = request.env['hr.leave'].with_user(2)

        domain = self._leaves_domain()
        
        searchbar_sortings = {
            'create_date': {'label': _('Create Date'), 'order': 'create_date desc'},
            'date_from': {'label': _('Leave Date'), 'order': 'date_from desc'},
            'type': {'label': _('Leave Type'), 'order': 'holiday_status_id asc'},
            'state': {'label': _('Leave Status'), 'order': 'state asc'},
            'duration': {'label': _('Duration'), 'order': 'duration_display asc'},
        }
        # default sort by order
        if not sortby:
            sortby = 'create_date'
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
        leaves_count = leaves_model.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/leaves",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=leaves_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager and archive selected
        leaves = leaves_model.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_leaves_history'] = leaves.ids[:100]

        # Check if user is an employee
        current_user = request.env.user
        employee = request.env['hr.employee'].with_user(2).search([('user_partner_id', '=', current_user.partner_id.id)], limit=1)
        
        values.update({
            'date': date_begin,
            'leaves': leaves,
            'leave_types': request.env['hr.leave.type'].search([]),
            'page_name': 'leave',
            'pager': pager,
            'default_url': '/my/leaves',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'is_readonly': kw.get('is_readonly', True),
            'has_employee': bool(employee)
        })
        return request.render("oo_portal_employees.portal_my_leaves", values)

    @http.route(['/my/leaves/<int:leave_id>'], type='http', auth="user", website=True)
    def portal_my_leave_details(self, leave_id=None, access_token=None, report_type=None, download=False, **kw):
        # If leave_id is 0, it's a new leave form request
        if leave_id == 0:
            # Check if user is an employee
            current_user = request.env.user
            employee = request.env['hr.employee'].with_user(2).search([('user_partner_id', '=', current_user.partner_id.id)], limit=1)
            if not employee:
                return request.redirect('/my')
            
            values = self._prepare_portal_layout_values()
            values.update({
                'leave_types': request.env['hr.leave.type'].search([]),
                'has_employee': bool(employee),
            })
            return request.render("oo_portal_employees.portal_leave_new_form", values)
        
        # Fetch the leave record - check user's own leaves and approved leaves if they're a manager
        leave_model = request.env['hr.leave'].with_user(2)
        current_user = request.env.user
        
        # If user is a leave manager, they can see all leaves; otherwise only their own
        is_leave_manager = (current_user.has_group('oo_portal_employees.group_portal_employee_leave_manager') or 
                           current_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        
        if is_leave_manager:
            # Manager can see any leave
            leave_sudo = leave_model.browse(leave_id).exists()
            if not leave_sudo:
                raise MissingError(f'Leave record {leave_id} not found.')
        else:
            # Regular user can only see their own leaves
            employee = request.env['hr.employee'].with_user(2).search([('user_partner_id', '=', current_user.partner_id.id)], limit=1)
            if not employee:
                raise MissingError('Missing employee record for this user.')
            leave_sudo = leave_model.search([('id', '=', leave_id), ('employee_id', '=', employee.id)], limit=1)
            if not leave_sudo:
                raise MissingError(f'Leave record {leave_id} not found or access denied.')

        values = self._leaves_get_page_view_values(leave_sudo, access_token, **kw)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=leave_sudo, report_type=report_type, report_ref='hr_payroll.action_report_payslip', download=download)
        return request.render("oo_portal_employees.portal_leave_page", values)
    
    @http.route(['/leaves/<int:leave_id>/cancel'], type='http', auth="user", website=True)
    def portal_leave_cancel(self, leave_id=None, access_token=None, report_type=None, download=False, **kw):
        leave_sudo = self._check_access_rights(leave_id, access_token)
        if not leave_sudo.can_cancel:
            raise ValidationError("You're not allowed to perform this action.")
        leave_sudo.with_user(2).action_cancel()
        return request.redirect('/my/leaves')

    @http.route(['/leaves/<int:leave_id>/refuse'], type='http', auth="user", website=True)
    def portal_leave_refuse(self, leave_id=None, access_token=None, **kw):
        leave_sudo = self._check_access_rights(leave_id, access_token)
        # Additional security: verify user is a leave approver
        current_user = request.env.user
        is_leave_manager = (current_user.has_group('oo_portal_employees.group_portal_employee_leave_manager') or 
                           current_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        if not is_leave_manager or leave_sudo.state in ['draft', 'refuse']:
            raise ValidationError("You're not allowed to perform this action.")
        leave_sudo.with_user(2).action_refuse()
        return request.redirect('/my/leaves')

    @http.route(['/leaves/<int:leave_id>/approve'], type='http', auth="user", website=True)
    def portal_leave_approve(self, leave_id=None, access_token=None, **kw):
        leave_sudo = self._check_access_rights(leave_id, access_token)
        # Additional security: verify user is a leave approver
        current_user = request.env.user
        is_leave_manager = (current_user.has_group('oo_portal_employees.group_portal_employee_leave_manager') or 
                           current_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        if not is_leave_manager or leave_sudo.state in ['draft', 'refuse', 'validate']:
            raise ValidationError("You're not allowed to perform this action.")
        leave_sudo.with_user(2).action_approve()
        return request.redirect('/my/leaves')
    
    @http.route(['/my/leaves/new'], type="http", auth="user", website=True, csrf=True)
    def portal_leave_new(self, **kw):
        leave_model = request.env['hr.leave'].with_user(2)
        employee = request.env['hr.employee'].with_user(2).search([('user_partner_id', '=', request.env.user.partner_id.id)], limit=1)
        if not employee:
            raise ValidationError('Missing required employee for this user.')
        
        # Parse dates
        date_from = parse(kw['date_from']).date() if isinstance(kw['date_from'], str) else kw['date_from']
        
        # Handle half day logic
        is_half_day = kw.get('request_unit_half') in ['true', 'True', True, 'on', '1']
        half_day_period = kw.get('request_date_from_period', 'am') if is_half_day else None
        
        # For half day, date_to should equal date_from; otherwise parse from kw
        if is_half_day:
            date_to = date_from
        else:
            date_to = parse(kw['date_to']).date() if isinstance(kw['date_to'], str) else kw['date_to']
            
        vals = {
            'employee_id': employee.id,
            'holiday_status_id': int(kw['holiday_status_id']),
            'request_unit_half': is_half_day,
            'request_date_from_period': half_day_period,
            'date_from': datetime.combine(date_from, datetime.min.time()),
            'request_date_from': datetime.combine(date_from, datetime.min.time()),
            'date_to': datetime.combine(date_to, datetime.max.time()),
            'request_date_to': datetime.combine(date_to, datetime.max.time()),
            'name': kw.get('name', ''),
        }
        
        _logger.info(f'creating new leave for employee {employee.name} with data {vals}')

        # Handle attachments
        attachments = []
        if kw.get("supported_attachment_ids"):
            for c_file in request.httprequest.files.getlist("supported_attachment_ids"):
                data = c_file.read()
                if c_file.filename:
                    attachment = request.env["ir.attachment"].sudo().create({
                        "name": c_file.filename,
                        "datas": base64.b64encode(data),
                        "res_model": "hr.leave",
                    })
                    attachments.append(attachment.id)

        if attachments:
            vals["supported_attachment_ids"] = [(6, 0, attachments)]
        
        leave = leave_model.create(vals)

        return request.redirect('/my/leaves')


