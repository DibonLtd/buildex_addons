# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError

import logging
import pytz
_logger = logging.getLogger(__name__)


class ZKTecoAttendance(models.Model):
    _name = 'zkteco.attendance.feed'
    _description = 'ZKTeco Feed'
    _order = 'create_date desc'

    name = fields.Char(string="Employee Id")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    timestamp = fields.Char(string="Timestamp")
    device_id = fields.Many2one('zkteco.device', string="Zkteco Device")
    state = fields.Selection([('new', 'New'), ('mark', 'Marked')], string="State", default="new", copy=False)
    attendance_id = fields.Many2one("hr.attendance", string="Attendance", copy=False)
    sid = fields.Char(string="User id")
    punch_state_data = fields.Char(string="Punch State")
    attendance_mark_type = fields.Selection([('manually', 'Manually'), ('cron', 'Cron'),('webhook','Webhook'),('cloud','Cloud')], string="Attendance Type", default=False, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('timestamp', False):
                timestamp = vals.get('timestamp', False)
                search = self.sudo().search([('timestamp','=',timestamp)])
                if search:
                    _logger.warning(f'Already created Feed')
                    raise UserError('A feed with the same time has already been created.')
        res = super().create(vals_list)
        for record in res:
            if record.name:
                employee_id = self.env['hr.employee'].sudo().search([('barcode', '=', record.name)], limit=1)
                record.employee_id = employee_id if employee_id else False
        return res

    def create_attendance(self):
        try:
            for att in self:
                if att.state == 'mark':
                    continue
                employee = self.env['hr.employee'].search([('barcode', '=', att.name)], limit=1)
                if not employee:
                    continue
                attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id)], order='id desc', limit=1)
                feed_linked = self.search([('attendance_id', '=', attendance.id)], limit=1)
                # Convert timestamp to datetime object
                timestamp_dt = fields.Datetime.from_string(att.timestamp)
                # convert to user timezone
                employee_tz = employee.tz or 'UTC'
                local_tz = pytz.timezone(employee_tz)
                localized_timestamp_dt = local_tz.localize(timestamp_dt)
                # convert to UTC timezone
                utc_timestamp_dt = localized_timestamp_dt.astimezone(pytz.UTC)
                naive_utc_timestamp_dt = utc_timestamp_dt.replace(tzinfo=None)

                if not attendance:
                    # Create new attendance if it doesn't exist
                    attendance = {
                        'employee_id': employee.id,
                        'check_in': naive_utc_timestamp_dt,
                        'in_mode': 'systray',
                        'in_ip_address': att.device_id.ip_address,
                    }
                    emp_att = self.env['hr.attendance'].create(attendance)
                    if emp_att:
                        # Handle break-in or break-out for new attendance
                        if att.punch_state_data in ['break_in', 'break_out']:
                            self._create_or_update_break(att, emp_att, naive_utc_timestamp_dt)

                        if att.punch_state_data in ['check_out']:
                            emp_att.check_out = naive_utc_timestamp_dt
                            emp_att.out_mode = 'systray'
                            emp_att.out_ip_address = att.device_id.ip_address
                    att.state = 'mark'
                    att.attendance_id = emp_att.id
                else:
                    # If attendance exists
                    if not attendance.check_out:
                        if att.punch_state_data in ['check_in']:
                            continue  # Skip if it's a check-in without check-out
                        if att.punch_state_data in ['break_in']:
                            self._create_or_update_break(att, attendance, naive_utc_timestamp_dt)
                        elif att.punch_state_data in ['break_out']:
                            self._handle_break_out(att, attendance, naive_utc_timestamp_dt)
                        elif att.punch_state_data in ['check_out', '']:
                            attendance.check_out = naive_utc_timestamp_dt
                            attendance.out_mode = 'systray'
                            attendance.out_ip_address = att.device_id.ip_address
                        if not att.punch_state_data:
                            attendance.check_out = naive_utc_timestamp_dt
                            attendance.out_mode = 'systray'
                            attendance.out_ip_address = att.device_id.ip_address
                        att.state = 'mark'
                        att.attendance_id = attendance.id
                    else:
                        attendance = {
                            'employee_id': employee.id,
                            'check_in': naive_utc_timestamp_dt,
                            'in_mode': 'systray',
                            'in_ip_address': att.device_id.ip_address,
                        }
                        emp_att = self.env['hr.attendance'].sudo().create(attendance)
                        if emp_att:
                            if att.punch_state_data in ['break_in', 'break_out']:
                                self._create_or_update_break(att, emp_att, naive_utc_timestamp_dt)
                            if att.punch_state_data in ['check_out']:
                                emp_att.check_out = naive_utc_timestamp_dt
                                emp_att.out_mode = 'systray'
                                emp_att.out_ip_address = att.device_id.ip_address
                        att.state = 'mark'
                        att.attendance_id = emp_att.id

            # return True
        except Exception as e:
            _logger.error(f"Error while creating attendance: {e}")
            return False

    def _create_or_update_break(self, att, attendance, timestamp):
        """ Create or update break records"""
        break_vals = {
            'break_in_time': timestamp,
            'attendance_id': attendance.id,
            'employee_id': attendance.employee_id.id,
        }
        if att.punch_state_data in ['break_out']:
            break_vals['break_out_time'] = timestamp
        self.env['hr.attendance.break'].sudo().create(break_vals)

    def _handle_break_out(self, att, attendance, timestamp):
        """ Handle incomplete break-out """
        if attendance.hr_break_ids:
            incomplete_break = attendance.hr_break_ids[-1] if attendance.hr_break_ids[-1].break_out_time == False else False
            if incomplete_break:
                incomplete_break = incomplete_break[-1]
                incomplete_break.break_out_time = timestamp
            else:
                self._create_or_update_break(att, attendance, timestamp)
        else:
            self._create_or_update_break(att, attendance, timestamp)
