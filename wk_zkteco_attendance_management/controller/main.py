# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import http
import json
from datetime import datetime
from odoo.http import request, Response
import logging
_logger = logging.getLogger(__name__)


class DeviceAttendance(http.Controller):

    @http.route(['/iclock/getrequest','/iclock/cdata'], methods=['POST', 'GET'], auth='public', csrf=False)
    def zkteco_get_attendance_data(self, **kw):
        # ['108152', '2025-05-05', '16:31:13', '1', '1', '0', '0', '0', '0', '0', '0'] 

        serial_number = kw.get('SN',False)
        _logger.info("=====kw=====%r", kw)
        if not serial_number:
            return False
        if request.httprequest.method == 'GET':
            return Response('OK', status=200, content_type='text/plain')
        if kw.get('table', False) in ['OPERLOG','options', 'BIODATA']:
            return Response('OK', status=200, content_type='text/plain')
        
        elif request.httprequest.method == 'POST':
            chunk_size = 11
            raw_data = request.httprequest.data.decode('utf-8')
            _logger.info("Attendance Data:\n%s", request.httprequest)
            created_val = []
            if not raw_data:
                return Response('False', status=400, content_type='text/plain')
            raw_data = raw_data.split()
            records = [raw_data[i:i + chunk_size] for i in range(0, len(raw_data), chunk_size)]
            device = request.env['zkteco.device'].sudo().search([('serial_number','=',serial_number)],limit=1)
            for record in records:
                if device:
                    if device.state == 'draft':
                        device.state = 'connected'
                    if '=' in record[1]:
                        continue
                    user_id = record[0]
                    timestamp = " ".join((record[1], record[2]))
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    feed_dict = {
                        'name': user_id,
                        'timestamp': timestamp,
                        'device_id': device.id,
                        'attendance_mark_type': 'cloud',
                    }
                    punch_value = record[3]
                    if device.punch_state_ids:
                        punch_data = device.punch_state_ids.filtered(lambda x:x.value == int(punch_value))
                        if punch_data:
                            punch_state = punch_data[0].punch_state
                            feed_dict['punch_state_data'] = punch_state
                    created_val.append(feed_dict)
            feeds = request.env['zkteco.attendance.feed'].sudo().create(created_val)
            for feed in feeds:
                feed.sudo().create_attendance()
            device.last_sync = datetime.now()              
        return Response('OK', status=200, content_type='text/plain')

    @http.route('/wk/zkteco/attendance', methods=['POST'], auth='public', csrf=False)
    def zkteco_attendance(self, **post):
        """
        [{'COMPANY_NAME': 'default', 'EMP_CODE': '108152', 'FIRST_NAME': 'test', 
        'PUNCH_DATE': '08-04-2025', 'PUNCH_TIME': '15:06:34', 'PUNCH_STATE': 'Check Out', 
        'AREA_NAME': 'wk', 'PUNCH_DATETIME': '08-04-2025 15:06:34', 'MASK_FLAG': '', 
        'UPLOAD_TIME': '2025-04-08 15:06:41.106705','TERMINAL_SN': ''}]
        """
        data = request.httprequest.data.decode('utf-8')
        data = data.replace("'", '"')
        data = json.loads(data)
        feed_vals = []
        for record in data:
            user_id = record.get('EMP_CODE',False)
            timestamp = record.get('PUNCH_DATETIME',False)
            serial_number = record.get('TERMINAL_SN',False)  ### TERMINAL_SN -->>> for testing
            if not serial_number:
                continue
            device = request.env['zkteco.device'].sudo().search([('serial_number','=',serial_number)],limit=1)
            if user_id and timestamp and device:
                timestamp = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
                feed_dict = {
                    'name': user_id,
                    'timestamp': timestamp,
                    'device_id': device.id,
                    'attendance_mark_type': 'webhook',
                }
                punch_state_label = record.get('PUNCH_STATE',False)
                if punch_state_label:
                    punch_state = punch_state_label.lower().replace(" ", "_")
                    punch_data = device.punch_state_ids.mapped('punch_state')
                    if punch_state in punch_data:
                        feed_dict['punch_state_data'] = punch_state
                feed_vals.append(feed_dict)
            feeds = request.env['zkteco.attendance.feed'].sudo().create(feed_vals)
            for feed in feeds:
                feed.sudo().create_attendance()
            device.last_sync = datetime.now()
