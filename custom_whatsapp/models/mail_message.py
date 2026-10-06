# See LICENSE file for full copyright and licensing details.

import ast
import base64
from odoo import fields, models, _, sql_db, api, tools
from odoo.tools.mimetypes import guess_mimetype
from odoo.exceptions import UserError
from datetime import datetime
import html2text
import threading
import requests
import json
import logging
from ..wgapi import texttohtml
from ..wgapi import WGApi

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    _ACTIVE_THRESHOLD_DAYS = 15

    message_type = fields.Selection(selection_add=[('whatsapp', 'Whatsapp')], ondelete={'whatsapp': 'set default'})   
    whatsapp_message_type = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound')], string="Message Type", default='outbound') 
    whatsapp_server_id = fields.Many2one('ir.whatsapp_server', string='Whatsapp Server')
    whatsapp_method = fields.Char('Method', default='sendMessage')
    whatsapp_status = fields.Selection([('pending','Pending'),('send', 'Sent'),('error', 'Error')], default='pending', string='Whatsapp Status')
    whatsapp_response = fields.Text('Response', readonly=True)
    whatsapp_data = fields.Text('Data', readonly=False)
    whatsapp_chat_id = fields.Char(string='ChatId')
    whatsapp_numbers = fields.Char()
    whatsapp_message_id = fields.Many2one('mail.message', string="Parent")
    wa_message_ids = fields.One2many('mail.message', 'whatsapp_message_id', string='Related WhatsApp Messages')

    # @api.model
    # def create(self, vals):
    #     # if vals.get('whatsapp_data'):
    #     #     vals['whatsapp_data'] = str(vals['whatsapp_data']).replace("'",'*').replace('"',"*")
    #     print ('===vals===',vals)
    #     return super(MailMessage, self).create(vals)
    
    # def _send(self, force_send_by_cron=False):
    #     if len(self) <= 1 and not force_send_by_cron:
    #         self._send_message()
    #     else:
    #         self.env.ref('aos_whatsapp.ir_cron_whatsapp_mail_message_erro_cron')._trigger()

    @api.model
    def _resend_whatsapp_message_resend(self, wgapi, unlink_failed=False, unlink_sent=True, raise_exception=False):
        try:
            # Use default environment and transaction management, do not create a new cursor
            with tools.mute_logger('odoo.sql_db'):
                MailMessage = self.env['mail.message'].search([('message_type','=','whatsapp'),('whatsapp_status', '=', 'pending')], limit=50)
                get_version = self.env["ir.module.module"].sudo().search([('name','=','base')], limit=1).latest_version
                for mail in MailMessage.filtered(lambda m: m.whatsapp_data):
                    try:
                        if not mail.whatsapp_data:
                            mail.whatsapp_status = 'error'
                            mail.whatsapp_response = 'No Message Datas'
                        data = str(mail.whatsapp_data).replace("'",'"')
                        try:
                            fixed_json_string = json.loads(data)
                            data = json.dumps(fixed_json_string, indent=4)
                        except json.JSONDecodeError as e:
                            _logger.warning("Invalid JSON: {e}")
                            mail.whatsapp_response = "Invalid JSON: {e}"
                        data = json.loads(data)
                        message_data = {
                            'client_secret': mail.whatsapp_server_id.dibon_secret,
                            'body': texttohtml.formatText(mail.body),
                            'phone': data.get('phone') or '',
                            'origin': data.get('origin') or '',
                            'link': data.get('link') or '',
                            'version': get_version,
                        }
                        if mail.whatsapp_method == 'sendFile' and mail.attachment_ids:
                            send_message_response = []
                            whatsapp_status = 'error'
                            i = 1
                            for attach in mail.attachment_ids:
                                mimetype = guess_mimetype(base64.b64decode(attach.datas))
                                if mimetype == 'application/octet-stream':
                                    mimetype = 'video/mp4'
                                str_mimetype = 'data:' + mimetype + ';base64,'
                                attachment = str_mimetype + str(attach.datas.decode("utf-8"))
                                message_data.update({
                                    'method': mail.whatsapp_method,
                                    'body': attachment, 
                                    'filename': attach.name, 
                                    'caption': data.get('caption') if i == 1 else '',
                                })
                                # data_message = json.dumps(message_data)
                                payload = {"params": message_data}
                                send_message = wgapi.post_request(token=mail.whatsapp_server_id.whatsapp_token, data=payload)
                                # send_message = wgapi.post_request(method=mail.whatsapp_method, data=data_message)
                                # print ('----',send_message)
                                if send_message.get('message')['sent']:
                                    whatsapp_status = 'send'
                                    send_message_response.append(attach.name + ': ' + str(send_message))
                                    # mail.whatsapp_response += send_message
                                    _logger.warning('%s. Success send Attachment %s to WhatsApp %s', str(i), attach.name, data.get('phone'))
                                else:
                                    whatsapp_status = 'error'
                                    send_message_response.append(attach.name + ': ' + str(send_message))
                                    # mail.whatsapp_response += send_message
                                    _logger.warning('%s. Failed send Attachment %s to WhatsApp %s', str(i), attach.name, data.get('phone'))
                                i += 1
                            # print ('==send_message_res?ponse==',send_message,whatsapp_status)
                            mail.whatsapp_status = whatsapp_status
                            mail.whatsapp_response = '\n'.join(send_message_response)
                        else:
                            #KLO GA ADA ATTACHMENT
                            # data_message = json.dumps(message_data)
                            message_data.update({'method': mail.whatsapp_method})
                            payload = {"params": message_data}
                            send_message = wgapi.post_request(token=mail.whatsapp_server_id.whatsapp_token, data=payload)
                            # print ('=send_message=',mail.whatsapp_server_id.whatsapp_token,message_data,send_message)
                            # send_message = wgapi.post_request(method=mail.whatsapp_method, data=data_message)
                            if send_message.get('message')['sent']:
                                mail.whatsapp_status = 'send'
                                mail.whatsapp_response = send_message
                                _logger.warning('Success send Message to WhatsApp %s', data.get('phone'))
                            else:
                                mail.whatsapp_status = 'error'
                                mail.whatsapp_response = send_message
                                _logger.warning('Failed send Message to WhatsApp %s', data.get('phone'))
                    finally:
                        pass
        finally:
            pass

    def _split_batch(self):
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.session.batch.size', 500))
        for sms_batch in tools.split_every(batch_size, self.ids):
            yield sms_batch

    def send_whatsapp(self, wgapi, unlink_failed=False, unlink_sent=True, auto_commit=False, raise_exception=False):
        """ Main API method to send SMS.

          :param unlink_failed: unlink failed SMS after IAP feedback;
          :param unlink_sent: unlink sent SMS after IAP feedback;
          :param auto_commit: commit after each batch of SMS;
          :param raise_exception: raise if there is an issue contacting IAP;
        """
        self = self.filtered(lambda wlog: wlog.whatsapp_status == 'pending')
        for batch_ids in self._split_batch():
            self.browse(batch_ids)._resend_whatsapp_message_resend(wgapi=wgapi, unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)
            # auto-commit if asked except in testing mode
            if auto_commit is True and not getattr(threading.current_thread(), 'testing', False):
                self._cr.commit()

    @api.model
    def resend_whatsapp_mail_message(self, ids=None):
        """ Send immediately queued messages, committing after each message is sent.
        This is not transactional and should not be called during another transaction!

       :param list ids: optional list of emails ids to send. If passed no search
         is performed, and these ids are used instead.
        """
        whatsapp_ids = self.env['ir.whatsapp_server'].sudo().search([('status','=','authenticated')], order='sequence asc', limit=1)
        domain = [('whatsapp_status', '=', 'pending')]

        filtered_ids = self.search(domain, limit=10000).ids  # TDE note: arbitrary limit we might have to update
        if ids:
            ids = list(set(filtered_ids) & set(ids))
        else:
            ids = filtered_ids
        ids.sort()

        res = None
        #print ('==whatsapp_ids==',whatsapp_ids)

        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            client = whatsapp_ids._get_wgapi_client()
            # Fix: use correct argument name for send_whatsapp
            res = self.browse(ids).send_whatsapp(wgapi=client, unlink_failed=False, unlink_sent=True, auto_commit=auto_commit, raise_exception=False)
        except Exception:
            _logger.exception("Failed processing Whatsapp queue")
        return res

    # @api.model
    # def resend_whatsapp_mail_message(self):
    #     """Resend whatsapp error message via threding.""" 
    #     WhatsappServer = self.env['ir.whatsapp_server']
    #     whatsapp_ids = WhatsappServer.sudo().search([('status','=','authenticated')], order='sequence asc')
    #     #if len(whatsapp_ids) == 1:            
    #     print ('===',whatsapp_ids,whatsapp_ids.filtered(lambda ws: not ast.literal_eval(str(ws.message_response))))
    #     try:
    #         # print ('==resend_whatsapp_mail_message==',whatsapp_ids.message_response,whatsapp_ids.mapped('message_response'))
    #         for wserver in whatsapp_ids:#.filtered(lambda ws: not ast.literal_eval(str(ws.message_response))['block']):
    #             #company_id = self.env.user.company_id
    #             if wserver.status != 'authenticated':
    #                 _logger.warning('Whatsapp Authentication Failed!\nConfigure Whatsapp Configuration in General Setting.')
    #             wgapi = wserver.wgapi()
    #             wgapi.auth()
    #             thread_start = threading.Thread(target=self._resend_whatsapp_message_resend(wgapi))
    #             thread_start.start()
    #     except Exception:
    #         _logger.exception('Error while checking whatapp connection')
    #     return True
        # for wserver in whatsapp_ids.filtered(lambda ws: not ast.literal_eval(str(ws.message_response))['block']):
        #     #company_id = self.env.user.company_id
        #     if wserver.status != 'authenticated':
        #         _logger.warning('Whatsapp Authentication Failed!\nConfigure Whatsapp Configuration in General Setting.')
        #     wgapi = wserver.wgapi()
        #     wgapi.auth()
        #     thread_start = threading.Thread(target=self._resend_whatsapp_message_resend(wgapi))
        #     thread_start.start()
        # return True

