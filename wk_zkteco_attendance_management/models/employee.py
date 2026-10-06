# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.resource.models.utils import Intervals
from pytz import timezone
import logging
_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    linked_machine_count = fields.Integer('Linked machine', compute="get_linked_machine")

    def get_linked_machine(self):
        for rec in self:
            linked_record = self.env['employee.machine.data'].search([('employee_id','=',rec.id)])
            rec.linked_machine_count = len(linked_record)

    def linked_machine(self):
        return {
            'name': 'Machines',
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'employee.machine.data',
            'context' : {'employee_page': True},
            'domain':
                [('employee_id', 'in', [self.id])]
        }

    @api.model_create_multi
    def create(self, val_list):
        for vals in val_list:
            vals['barcode'] = self.env['ir.sequence'].next_by_code('hr.employee.barcode')
        res = super(HrEmployee, self).create(val_list)
        return res

    def _create_employee_pin_cron(self):
        employees = self.sudo().search([('barcode', '=', False)])
        for emp in employees:
            emp.barcode = self.env['ir.sequence'].next_by_code('hr.employee.barcode')

    # @api.constrains('barcode')
    # def _constrains_pin_unique(self):
    #     for rec in self:
    #         employee = self.search([('barcode', '=', rec.barcode)])
    #         if len(employee) > 1:
    #             raise UserError(f"An employee with the PIN {rec.barcode} already exists. Each employee must have a unique PIN code.")


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    hr_break_ids = fields.One2many('hr.attendance.break', 'attendance_id', string='Break Attendance')
    break_hours = fields.Float(string='Break Hours', compute='_compute_break_hours', store=True)

    @api.depends('hr_break_ids', 'hr_break_ids.break_duration')
    def _compute_break_hours(self):
        for rec in self:
            if rec.hr_break_ids:
                rec.break_hours = sum(rec.hr_break_ids.mapped('break_duration'))
            else:
                rec.break_hours = 0

    @api.depends('check_in', 'check_out', 'break_hours')
    def _compute_worked_hours(self):
        super()._compute_worked_hours()
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                resource = attendance.employee_id.resource_id
                tz = timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                # lunch_intervals = attendance.employee_id._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=True)
                # attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)])
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)
                if attendance.break_hours:
                    attendance.worked_hours = (delta / 3600.0) - attendance.break_hours
                else:
                    attendance.worked_hours = delta / 3600.0
            else:
                attendance.worked_hours = False
