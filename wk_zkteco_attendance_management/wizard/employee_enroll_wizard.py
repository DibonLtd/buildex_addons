# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class PanarabiaRequestWizard(models.TransientModel):
    _name = "enroll.employees.wizard"
    _description = "Enroll Employees Wizard"

    employee_ids = fields.Many2many('hr.employee', string="Employees")

    def enroll_selected_employees(self):
        for record in self:
            if self._context:
                active_id = self._context.get('active_id', False)
                device_record = self.env['zkteco.device'].browse(active_id)
                if not device_record:
                    return False
                res = device_record.connect_device()
                if res:
                    if not record.employee_ids:
                        return False
                    for rec in record.employee_ids:
                        pin = rec.barcode
                        set_user = res.set_user(uid=rec.id, name=rec.name, user_id=pin, card=pin)
                    device_record.fetch_employees()
                else:
                    _logger.warning('Device is not connected')

    def delete_selected_employees(self):
        for record in self:
            if self._context:
                active_id = self._context.get('active_id', False)
                device_record = self.env['zkteco.device'].browse(active_id)
                if not device_record:
                    return False
                res = device_record.connect_device()
                if res:
                    if not record.employee_ids:
                        return False
                    for rec in record.employee_ids:
                        pin = rec.barcode
                        remove_user = res.delete_user(user_id=pin)
                    device_record.fetch_employees()
                else:
                    _logger.warning('Device is not connected')
