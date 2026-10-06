# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields
from odoo.exceptions import UserError
from zk import ZK, const
import logging
_logger = logging.getLogger(__name__)


class ZKTecoDevice(models.Model):
    _name = 'zkteco.device'
    _description = 'ZKTeco Device'

    name = fields.Char(string='Device Name')
    ip_address = fields.Char(string='IP Address')
    port = fields.Char(string='Port', default=4370)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'New'), ('connected', 'Connected'), ('error', 'Error')], default="draft"
    )
    serial_number = fields.Char(string='Serial Number') 
    last_sync = fields.Datetime(string='Last Sync')
    last_attendance_id = fields.Integer(string='Last Attendance', default=0)
    punch_state_ids = fields.One2many('machine.punch.state', 'machine_id', string='Punch State')
    machine_user_ids = fields.One2many('employee.machine.data', 'machine_id', string='Machine Users')
    linked_feed_count = fields.Integer('Feeds', compute="compute_linked_feed_count")
    is_adms_mode = fields.Boolean('ADMS')

    def compute_linked_feed_count(self):
        for rec in self:
            linked_feeds = self.env['zkteco.attendance.feed'].search([('device_id','=',rec.id)])
            rec.linked_feed_count = len(linked_feeds)

    def test_connection(self):
        self.ensure_one()
        res = self.connect_device()
        if not res:
            self.state = 'error'
        else:
            self.get_device_information(res)
            self.state = 'connected'
            self.disconnect_device(res)

    def action_linked_machine_user(self):
        return {
            'name': 'Machine Users',
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'employee.machine.data',
            'domain':
                [('id', 'in', self.machine_user_ids.ids)]
        }
    
    def action_linked_feeds(self):
        return {
            'name': 'Feeds',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree.form',
            'res_model': 'zkteco.attendance.feed',
            'views': [(self.env.ref('wk_zkteco_attendance_management.view_zkteco_attendance_feed_tree').id, 'list'), (self.env.ref('wk_zkteco_attendance_management.view_zkteco_attendance_feed_form').id, 'form')],
            'domain':
                [('device_id', '=', self.id)]
        }

    def enroll_employees(self):
        self.ensure_one()
        employees_with_pin = self.env['hr.employee'].search([('barcode', '!=', False), ('id', 'not in', self.machine_user_ids.mapped('employee_id').ids)])
        if employees_with_pin:
            create_data = {
                    'employee_ids': [(6, 0, employees_with_pin.ids)]
                }
            context = {'button_display': 'enroll'}
            enrollment_wizard = self.env['enroll.employees.wizard'].create(create_data)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Enroll Employees',
                'res_model': 'enroll.employees.wizard',
                'view_mode': 'form',
                'res_id': enrollment_wizard.id,
                'target': 'new',
                'context': context,
            }

    def delete_employees(self):
        self.ensure_one()
        linked_employees = self.env['hr.employee'].search([('barcode', '!=', False),('id', 'in', self.machine_user_ids.mapped('employee_id').ids)])
        if linked_employees:
            create_data = {
                    'employee_ids': [(6, 0, linked_employees.ids)]
                }
            context = {'button_display' : 'remove'}
            enrollment_wizard = self.env['enroll.employees.wizard'].create(create_data)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Remove Employees',
                'res_model': 'enroll.employees.wizard',
                'view_mode': 'form',
                'res_id': enrollment_wizard.id,
                'target': 'new',
                'context': context,
            }

    def fetch_employees(self):
        self.ensure_one()
        res = self.connect_device()
        if res:
            user_data = []
            existing_user_ids = set(self.machine_user_ids.mapped('user_id'))
            machine_users = res.get_users()
            machine_data = []
            if machine_users:
                new_user_ids = set()
                for user in machine_users:
                    name = user.name
                    user_id = user.user_id
                    if user_id not in existing_user_ids:
                        user_data.append({
                            'name': name,
                            'user_id': user_id,
                            'machine_id': self.id,
                        })
                        existing_user_ids.add(user_id)
                    new_user_ids.add(user_id)
                if user_data:
                    machine_users = self.env['employee.machine.data'].create(user_data)
                    machine_data.append(machine_users)
                    user_ids = [u['user_id'] for u in user_data]
                    employees = self.env['hr.employee'].search([('barcode', 'in', user_ids)])
                    pin_employee_map = {emp.barcode: emp for emp in employees}
                    for user in machine_users:
                        employee = pin_employee_map.get(user.user_id)
                        if employee:
                            user.employee_id = employee.id

                # Already removed User Via machine
                current_user_ids = set(self.machine_user_ids.mapped('user_id'))
                removed_user_ids = current_user_ids - new_user_ids
                if removed_user_ids:
                    self.env['employee.machine.data'].search([
                        ('user_id', 'in', list(removed_user_ids)),
                        ('machine_id', '=', self.id)
                    ]).unlink()
                if machine_data:
                    self.machine_user_ids = [(6, 0, self.machine_user_ids.ids + machine_data[0].ids)]

    def get_device_information(self, zk):
        name = zk.get_device_name()
        serial = zk.get_serialnumber()
        self.name = name
        self.serial_number = serial

    def action_clear_machine_data(self):
        for rec in self:
            res = rec.connect_device()
            if res:
                response = res.clear_data()
                if response != True:
                    raise UserError(response)

    def reset(self):
        for obj in self:
            if obj.state in ['connected', 'error']:
                obj.state = 'draft'

    def connect_device(self):
        zk = ZK(self.ip_address, int(self.port))
        try:
            res = zk.connect()
            if res:
                return zk
            else:
                return None
        except Exception as e:
            _logger.warning("Error while creating connetion :- %r", e)
            return None

    def disconnect_device(self, zk):
        zk.disconnect()

    def get_attendance(self):
        zk = self.connect_device()
        if zk:
            zk.disable_device()
            attendance = zk.get_attendance()
            zk.clear_attendance()
            zk.enable_device()
            self.disconnect_device(zk)
            return attendance
        else:
            return []

    def sync_attendance(self):
        attendances = self.get_attendance()
        last_attendance_id = self.last_attendance_id
        feed_vals = []
        for att in attendances:
            # Set uid, user_id, status, timestamp, punch, state
            user_id = att.user_id
            timestamp = att.timestamp
            status = att.uid
            punch_state = ''
            punch_value = att.punch
            if self.punch_state_ids:
                punch_data = self.punch_state_ids.filtered(lambda x:x.value == int(punch_value))
                if punch_data:
                    punch_state = punch_data[0].punch_state
            time_search = self.env['zkteco.attendance.feed'].search([('timestamp', '=', timestamp)])
            if time_search:
                continue
            if status > self.last_attendance_id:
                employee_id = self.env['hr.employee'].search([('barcode', '=', user_id)], limit=1)
                punch = {
                    'name': user_id,
                    'timestamp': timestamp,
                    'device_id': self.id,
                    'sid': status,
                    'employee_id': employee_id.id if employee_id else False,
                    'punch_state_data': str(punch_state),
                    'attendance_mark_type': 'manually',
                }
                if self.env.context.get('cron'):
                    punch['attendance_mark_type'] = 'cron'
                feed_vals.append(punch)
        feeds = self.env['zkteco.attendance.feed'].create(feed_vals)
        for feed in feeds:
            feed.create_attendance()
        self.last_sync = fields.Datetime.now()
        self.last_attendance_id = last_attendance_id

    def _sync_attendance_cron(self):
        devices = self.search([('state', '=', 'connected')])
        for device in devices:
            device.with_context(cron=True).sync_attendance()
