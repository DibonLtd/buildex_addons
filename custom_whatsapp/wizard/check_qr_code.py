import base64
# import functools
import io
import qrcode
from odoo import models, api, _, sql_db, fields
from odoo.exceptions import UserError, ValidationError
import requests
import json
import re
import time
import logging

_logger = logging.getLogger(__name__)


class WhatsAppQR(models.TransientModel):
    _name = "whatsapp.qr.wizard"
    _description = "WhatsApp QR Code Wizard"
    
    whatsapp_server_id = fields.Many2one('ir.whatsapp_server')
    qr_code = fields.Text('QR Code')
    qr_scan = fields.Binary(
        attachment=False, store=True, readonly=True,
        compute='_compute_qrcode',
    )
    whatsapp_number = fields.Char(string="Whatsapp Number")
    status = fields.Selection([
        ('init','Initial Status'),
        ('loading', 'Loading'),
        ('got qr code', 'QR Code'),
        ('authenticated', 'Authenticated')
    ], default='init')
    notes = fields.Text('Error Message', readonly=True)

    def _compute_qrcode(self):
        """Generate QR code for WhatsApp Web authentication"""
        for record in self:
            _logger.info(f"[QR Wizard] _compute_qrcode called for record {record.id}, qr_code: {record.qr_code}")
            if record.qr_code:
                qr_val = record.qr_code
                if qr_val.startswith('data:image/png;base64,'):
                    qr_base64 = qr_val.split('data:image/png;base64,')[1]
                    _logger.info(f"[QR Wizard] Detected base64 QR image for record {record.id}, length: {len(qr_base64)}")
                    record.qr_scan = qr_base64
                else:
                    _logger.info(f"[QR Wizard] Generating QR image from raw string for record {record.id}")
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(qr_val)
                    qr.make(fit=True)
                    img = qr.make_image()
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    qr_image = base64.b64encode(buffer.getvalue())
                    record.qr_scan = qr_image
                    _logger.info(f"[QR Wizard] Generated QR image for record {record.id}, length: {len(qr_image)}")
            else:
                _logger.info(f"[QR Wizard] No qr_code for record {record.id}, setting qr_scan to False")
                record.qr_scan = False

    def check_connection(self):
        """Check WhatsApp connection status and handle QR code generation"""
        self.ensure_one()
        whatsapp_server = self.env['ir.whatsapp_server'].sudo().search([], order='sequence asc', limit=1)
        self.whatsapp_server_id = whatsapp_server.id
        if not whatsapp_server:
            raise UserError(_('Please configure WhatsApp Server in General Settings'))
        try:
            client = whatsapp_server._get_wgapi_client()
            qr_response = client.get_qr_code()
            _logger.info('QR Response: %s', qr_response)
            if qr_response.get('status') == 'connected':
                _logger.info('[QR Wizard] QR code scanned, WhatsApp API returned connected: %s', qr_response)
                self.status = 'authenticated'
                whatsapp_server.write({
                    'connection_status': 'connected',
                    'status': 'authenticated',
                    'qr_scan': False
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('WhatsApp connection authenticated successfully!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            elif qr_response.get('status') == 'got qr code':
                self.status = 'got qr code'
                self.qr_code = qr_response.get('qrCode') or qr_response.get('qr')
                self._compute_qrcode()
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Scan QR Code'),
                    'res_model': self._name,
                    'view_mode': 'form',
                    'view_id': self.env.ref('custom_whatsapp.view_whatsapp_qr_wizard_form').id,
                    'res_id': self.id,
                    'target': 'new',
                }
            else:
                self.status = 'loading'
                self.notes = qr_response.get('message', _('Could not get QR code. Please try again.'))
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Connection Error'),
                    'res_model': self._name,
                    'view_mode': 'form',
                    'view_id': self.env.ref('custom_whatsapp.view_whatsapp_qr_wizard_form').id,
                    'res_id': self.id,
                    'target': 'new',
                }
        except Exception as e:
            _logger.error('WhatsApp connection error: %s', str(e))
            self.status = 'init'
            self.notes = str(e)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Connection Error'),
                'res_model': self._name,
                'view_mode': 'form',
                'view_id': self.env.ref('custom_whatsapp.view_whatsapp_qr_wizard_form').id,
                'res_id': self.id,
                'target': 'new',
            }
