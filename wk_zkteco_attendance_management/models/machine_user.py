# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

PUNCH_STATE_TYPE = [
    ('check_in', "Check In"),
    ('check_out', "Check Out"),
    ('break_in', "Break In"),
    ('break_out', "Break Out"),
]


class MachineUser(models.Model):
    _name = 'employee.machine.data'
    _description = 'Employee Machine Data'

    name = fields.Char(string='User Name')
    machine_id = fields.Many2one('zkteco.device', string='Machine')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    user_id = fields.Char(string='Badge ID')

    @api.onchange('employee_id')
    def onchange_employee(self):
        for rec in self:
            if rec.employee_id and rec.user_id:
                rec.employee_id.barcode = rec.user_id


class PunchState(models.Model):
    _name = 'machine.punch.state'
    _description = 'Machine Punch state'

    punch_state = fields.Selection(PUNCH_STATE_TYPE, string="Punch State")
    value = fields.Integer('Value')
    machine_id = fields.Many2one('zkteco.device', string="Machine")
