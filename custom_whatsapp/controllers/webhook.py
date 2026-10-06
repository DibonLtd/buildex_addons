from odoo import http
from odoo.http import request, route
import logging
import json
_logger = logging.getLogger(__name__)

class WhatsAppWebhookController(http.Controller):
    @route('/custom_whatsapp/webhook/session', type='http', auth='public', csrf=False, methods=['POST'])
    def whatsapp_session_webhook(self, **post):
        raw_body = request.httprequest.get_data(as_text=True)
        _logger.info('[WEBHOOK] Raw HTTP body: %s', raw_body)
        _logger.info('[WEBHOOK] Headers: %s', dict(request.httprequest.headers))
        try:
            data = json.loads(raw_body)
        except Exception as e:
            _logger.error('[WEBHOOK] Failed to parse JSON: %s', e)
            data = {}
        _logger.info('[WEBHOOK] Parsed data: %s', data)
        session = data.get('session')
        status = data.get('status')
        _logger.info('[WEBHOOK] Received session webhook: session=%s, status=%s', session, status)
        server = request.env['ir.whatsapp_server'].sudo().search([('session_name', '=', session)], limit=1)
        if server:
            # Only write allowed values to the 'status' field
            allowed_status = ['init', 'loading', 'got qr code', 'authenticated']
            status_map = {
                'connecting': 'loading',
                'got qr code': 'got qr code',
                'authenticated': 'authenticated',
                'init': 'init',
                'connected': 'authenticated',
                'disconnected': 'init',
            }
            odoo_status = status_map.get(status, None)
            vals = {'connection_status': status}
            if odoo_status in allowed_status:
                vals['status'] = odoo_status
            server.write(vals)
            _logger.info('[WEBHOOK] Updated ir.whatsapp_server %s to status=%s, connection_status=%s', server.id, vals.get('status'), vals.get('connection_status'))
            # Also update all open QR wizards for this server
            wizards = request.env['whatsapp.qr.wizard'].sudo().search([
                ('whatsapp_server_id', '=', server.id),
                ('status', '!=', 'authenticated')
            ])
            if status == 'connected':
                wizards.write({'status': 'authenticated', 'notes': 'Connected via webhook'})
                _logger.info('[WEBHOOK] Updated %d QR wizards to authenticated', len(wizards))
            elif status == 'connecting':
                wizards.write({'status': 'loading', 'notes': 'Connecting...'})
                _logger.info('[WEBHOOK] Updated %d QR wizards to loading', len(wizards))
            elif status == 'disconnected':
                wizards.write({'status': 'init', 'notes': 'Disconnected'})
                _logger.info('[WEBHOOK] Updated %d QR wizards to init', len(wizards))
        else:
            _logger.warning('[WEBHOOK] No ir.whatsapp_server found for session=%s', session)
        return request.make_response('{"result": "ok"}', headers=[('Content-Type', 'application/json')])
