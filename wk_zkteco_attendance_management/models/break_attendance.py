# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class HrAttendanceBreak(models.Model):
    _name = 'hr.attendance.break'
    _description = 'Manage Break Attendance'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    break_in_time = fields.Datetime(string='Break In')
    break_out_time = fields.Datetime(string='Break Out')
    break_duration = fields.Float(string='Break Duration', compute='_compute_break_duration', store=True)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance ID')

    @api.depends('break_in_time', 'break_out_time')
    def _compute_break_duration(self):
        for rec in self:
            if rec.break_in_time and rec.break_out_time:
                delta = rec.break_out_time - rec.break_in_time
                rec.break_duration = delta.total_seconds() / 3600.0
            else:
                rec.break_duration = 0.0
