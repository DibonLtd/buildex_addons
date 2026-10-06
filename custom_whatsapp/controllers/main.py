# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import hmac
import json
import logging
from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from http import HTTPStatus
from odoo import http, _
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class Webhook(http.Controller):

    @http.route('/webhook/test', type="json", auth='public', methods=['POST'])
    def some_html(self, **kw):
        return {
            'success': True,
            'status': 'OK',
            'code': 200
        }
    
    @http.route('/webhook/partner', type="json", auth='public', methods=['GET'])
    def webhook_partner(self, **kw):
        get_param = request.env['ir.config_parameter'].sudo().get_param('webhook.url')
        # print ('==s==',get_param,kw)
        return {
            'success': True,
            'status': 'OK',
            'webhook': get_param,
            'code': 200
        }
        

    def _get_available_users(self):
        """ get available user of a given channel
            :retuns : return the res.users having their im_status online
        """
        return request.env['discuss.channel'].sudo().search([], limit=1).user_ids#.filtered(lambda user: user.im_status == 'online')

    @http.route('/whatsapp/webhook/', methods=['POST'], type="json", auth="public")
    def webhookpost(self, **kwargs):
        #FOR RECEIPT MESSAGE FROM CUSTOMER
        data = json.loads(request.httprequest.data)
        if not kwargs:
            return request.make_response(
                data=json.dumps({'error': 'No Data'}),
                headers=[('Content-Type', 'application/json')]
            )
        uuid = kwargs.get('uuid')
        api_key = kwargs.get('x-api-key')
        sender = kwargs.get('sender')
        recipient = kwargs.get('recipient')
        sendermessage = kwargs.get('message')
        senderkeyhash = kwargs.get('senderkeyhash')
        recipientkeyhash = kwargs.get('recipientkeyhash')
        sendername = kwargs.get('sendername')
        message_type = kwargs.get('type')
        filename = kwargs.get('filename')
        body = kwargs.get('body')
        value = {
            "message_type": message_type,
            "uuid": uuid, 
            "x-api-key": api_key, 
            "sender": sender, 
            "recipient": recipient,
            "messages": sendermessage if sendermessage != 'undefined' else '',
            "sendername": sendername,
            "senderkeyhash": senderkeyhash, 
            "recipientkeyhash": recipientkeyhash,
        }
        domain = [('status','=','authenticated')]
        if recipient:
            domain += [('whatsapp_number','=',recipient)]
        account = request.env['ir.whatsapp_server'].sudo().search(domain, order='sequence asc', limit=1)
        # if not self._check_signature(account):
        #     raise Forbidden()
        # Attachment = request.env['ir.attachment'].sudo()
        attachments = []
        if body and 'base64' in body:
            datas_fname = body.split(',')[1]
            attachments = [(filename, base64.b64decode(datas_fname))]
        MailChannel  = account._process_messages(value, attachments).sudo()
        # print ('==MailChannel==',MailChannel)
        response_data = {
            'uuid': MailChannel.uuid,
            # 'user_id': user_id,
        }
        return response_data