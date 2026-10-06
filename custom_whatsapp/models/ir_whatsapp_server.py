# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
# import functools
import io
import qrcode
# import requests
from email import encoders
from email.charset import Charset
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formataddr, formatdate, getaddresses, make_msgid
import logging
import re
import smtplib
import json
import threading
from datetime import timedelta
from ..wgapi import WGApi

import html2text

from odoo import api, Command, fields, models, tools, _, sql_db
from odoo.exceptions import ValidationError, UserError
from odoo.tools import ustr, pycompat

import datetime
_logger = logging.getLogger(__name__)

SMTP_TIMEOUT = 60

class IrWhatsappServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""
    _name = "ir.whatsapp_server"
    _description = 'Whatsapp Server'

    name = fields.Char(string='Description', required=True, index=True)
    sequence = fields.Integer(string='Priority', default=10, help="When no specific mail server is requested for a mail, the highest priority one "
                                                                  "is used. Default priority is 10 (smaller number = higher priority)")
    active = fields.Boolean(default=True)
    # gateway_url = fields.Char("Gateway URL", default="Gateway URL", default="https://whatsapp-gateway.dibon.co.ke", required=True, help="URL of the WhatsApp Gateway server")
    gateway_url = fields.Char(
        "Gateway URL",
        default="https://whatsapp-gateway.dibon.co.ke",
        required=True,
        help="URL of the WhatsApp Gateway server"
    )
    session_name = fields.Char("Session Name", required=True, help="Name of the WhatsApp session")
    client_secret = fields.Char("Client Secret", help="Secret key for gateway authentication")
    qr_scan = fields.Text("QR Scan")
    connection_status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('connecting', 'Connecting'),
        ('connected', 'Connected')
    ], string='Connection Status', default='disconnected', readonly=True)
    # qrcode = fields.Binary(
    #     attachment=False, store=True, readonly=True,
    #     compute='_compute_qrcode',
    # )
    whatsapp_number = fields.Char('Whatsapp Number')
    whatsapp_webhook = fields.Char('Whatsapp Webhook')
    whatsapp_token = fields.Text('Whatsapp Token')
    status = fields.Selection([('init','Initial Status'),
                               ('loading', 'Loading'),
                               ('got qr code', 'QR Code'),
                               ('authenticated', 'Authenticated')], default='init', string="Status")
    hint = fields.Char(string='Hint', readonly=True, default="Configure Token and Instance")
    message_ids = fields.One2many('mail.message', 'whatsapp_server_id', string="Mail Message")    
    message_counts = fields.Integer('Message Sent Counts', compute='_get_mail_message_whatsapp')
    message_response = fields.Text('Message Response', compute='_get_mail_message_whatsapp')
    allowed_user_ids = fields.Many2many('res.users', 'allowed_user_ids_rel', string="Allowed Users",
        domain=[('share', '=', False)])
    notify_user_ids = fields.Many2many('res.users', 'notify_user_ids_rel', string="Channel Notification", default=lambda self: self.env.user,
        domain=[('share', '=', False)], required=True,
        help="Users to notify when a message is received and there is no template send in last 15 days")
    notes = fields.Text(readonly=True)
    # cron_connection_id = fields.Many2one('ir.cron', string="Cron Connection")

    def _check_whatsapp_number_exist(self):
        """Method to check mobile is on whatsapp."""
        number_dict = {}
        if self.whatsapp_number and self.connection_status == 'connected':
            client = self._get_wgapi_client()
            try:
                result = client.auth()
                number_dict = {'status': result.get('status', 'error')}
            except Exception:
                number_dict = {'status': 'error'}
        return number_dict

    @api.model
    def _find_default_for_server(self):
        return [
            # ('model', '=', model_name),
            # ('wa_template', '=', True),
            ('status','=','authenticated'),
            '|',
                ('allowed_user_ids', '=', False),
                ('allowed_user_ids', 'in', self.env.user.ids)
        ]

    
    def _get_mail_message_whatsapp(self):
        for was in self:
            try:
                client = was._get_wgapi_client()
                result = client.auth()
                was.message_counts = len(was.message_ids)
                was.message_response = result.get('status', 'disconnected')
            except Exception:
                was.message_counts = 0
                was.message_response = 'error'

    
    def _formatting_mobile_number(self, number):
        for rec in self:
            module_rec = self.env['ir.module.module'].sudo().search_count([
                ('name', '=', 'crm_phone_validation'),
                ('state', '=', 'installed')])
            country_code = str(rec.partner_id.country_id.phone_code)# if rec.partner_id.country_id else str(self.company_id.country_id.phone_code)
            country_count = len(str(rec.partner_id.country_id.phone_code))
            whatsapp_number = rec.partner_id.whatsapp
            if rec.partner_id.whatsapp[:country_count] == str(rec.partner_id.country_id.phone_code):
                #COUNTRY CODE 
                whatsapp_number = rec.partner_id.whatsapp
            elif rec.partner_id.whatsapp[0] == '0':
                #COUNTRY CODE
                if rec.partner_id.whatsapp[1:country_count+1] == str(rec.partner_id.country_id.phone_code):
                    #COUNTRY CODE 
                    whatsapp_number = rec.partner_id.whatsapp[1:]
                else:
                    whatsapp_number = country_code + rec.partner_id.whatsapp[1:]
            return whatsapp_number
            # return module_rec and re.sub("[^0-9]", '', number) or \
            #     str(rec.partner_id.country_id.phone_code
            #         ) + number

    def wgapi(self):
        """Get WGApi client instance"""
        return WGApi(
            gateway_url=self.gateway_url,
            session_name=self.session_name,
            client_secret=self.client_secret,
            server=self,
        )

    # Button function to trigger the delayed action
    # def _create_cron_connection_up(self):
    #     # Scheduling the cron job after 45 seconds
    #     check_cron = self.env['ir.cron'].search([('name','=','Connection Up')])
    #     if check_cron:
    #         # check_cron.active = True
    #         check_cron.nextcall = (datetime.datetime.now() + datetime.timedelta(seconds=15)).strftime('%Y-%m-%d %H:%M:%S')
    #         return check_cron
    #     self.env['ir.cron'].create({
    #         'name': 'Connection Up',
    #         'model_id': self.env['ir.model'].search([('model', '=', 'ir.whatsapp_server')], limit=1).id,
    #         'state': 'code',
    #         'code': 'model.run_connection_up(%s)' % self.whatsapp_number,  # This calls the delayed function
    #         'interval_type': 'minutes',
    #         'nextcall': (datetime.datetime.now() + datetime.timedelta(seconds=45)).strftime('%Y-%m-%d %H:%M:%S'),
    #         'numbercall': 1,
    #     })

    # The actual delayed function
    # def run_connection_up(self):
    #     _logger.info("Connection up function is executed after 30 seconds")
    #     WGApi = self.wgapi()
    #     WGApi.auth()
    #     # for record in self:
    #         # Do your processing here
    #     _logger.info(f"Processing record with ID: {self.id}")
    #     response = WGApi.get_request(method='connection_up', data={})
    #     _logger.info(f"Response Connection with ID {response.get}")
    #         # if record.cron_connection_id:
    #         #     record.cron_connection_id.unlink()

    def redirect_whatsapp_key(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://dibon.co.ke/shop/product/whatsapp-api-v1',
            'target': '_new',
        }
        
    @api.model
    def _send_whatsapp(self, numbers, message):
        """ Send whatsapp """
        WGApi = self.wgapi()
        # WGApi.auth()
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        for number in numbers:
            whatsapp = self._formatting_mobile_number(number)
            message_data = {
                'phone': whatsapp,
                'body': html2text.html2text(message),
            }
            data_message = json.dumps(message_data)
            send_message = WGApi.post_request(method='sendMessage', data=data_message)
            if send_message.get('message')['sent']:
                _logger.warning('Success to send Message to WhatsApp number %s', whatsapp)
            else:
                _logger.warning('Failed to send Message to WhatsApp number %s', whatsapp)
            new_cr.commit()
        return True

    
    def _find_active_channel(self, sender_mobile_formatted, sender_name=False, create_if_not_found=False):
        """This method will find the active channel for the given sender mobile number."""
        allowed_old_msg_date = fields.Datetime.now() - timedelta(days=self.env['mail.message']._ACTIVE_THRESHOLD_DAYS)
        whatsapp_message = self.env['mail.message'].sudo().search(
            [
                # ('mobile_number_formatted', '=', sender_mobile_formatted),
                ('message_type','=','whatsapp'),
                ('create_date', '>', allowed_old_msg_date),
                # ('wa_template_id', '!=', False),
                # ('whatsapp_message_type','=',''),
                # ('state', 'not in', ['outgoing', 'error', 'cancel']),
            ], limit=1, order='id desc')
        return self.env['discuss.channel'].sudo()._get_whatsapp_channel(
            whatsapp_number=sender_mobile_formatted,
            wa_account_id=self,
            sender_name=sender_name,
            create_if_not_found=create_if_not_found,
            related_message=whatsapp_message.whatsapp_message_id,
        )

    def _process_messages(self, value, attachments):
        """
            This method is used for processing messages with the values received via webhook.
            If any whatsapp message template has been sent from this account then it will find the active channel or
            create new channel with last template message sent to that number and post message in that channel.
            And if channel is not found then it will create new channel with notify user set in account and post message.
            Supported Messages
             => Text Message
             => Attachment Message with caption
             => Location Message
             => Contact Message
             => Message Reactions
        """
        # if 'messages' not in value and value.get('whatsapp_business_api_data', {}).get('messages'):
        #     value = value['whatsapp_business_api_data']

        # wa_api = WhatsAppApi(self)

        messages = value.get('messages', [])
        parent_id = False
        channel = False
        # print ('===messages===',value)
        sender_name = value['sendername']#value.get('contacts', [{}])[0].get('profile', {}).get('name')
        sender_mobile = value['sender']
        message_type = value['message_type']
        # message_type = value['type']
        if 'context' in messages:
            # parent_whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', messages['context'].get('id'))])
            # if parent_whatsapp_message:
            #     parent_id = parent_whatsapp_message.mail_message_id
            if parent_id:
                channel = self.env['discuss.channel'].sudo().search([('message_ids', 'in', parent_id.id)], limit=1)
        if not channel:
            # channel_domain = []
            # channel = self.env['mail.channel'].sudo().search(channel_domain, order='create_date desc', limit=1)
            channel = self._find_active_channel(sender_mobile, sender_name=sender_name, create_if_not_found=True)
        #     channel.wa_account_id = self.id
        # responsible_partners = self.notify_user_ids.mapped('partner_id')
        # if responsible_partners:
        #     channel = channel.filtered(lambda c: all(r in c.channel_member_ids.partner_id for r in responsible_partners))
        # partners_to_notify = responsible_partners
        #print ('==channel==',channel,messages)
        kwargs = {
            'email_from': sender_name,
            'record_name': sender_name,
            'author_id': self.env['res.partner'].search([('whatsapp','=',sender_mobile)], limit=1).id,#channel.whatsapp_partner_id.id,
            'subtype_xmlid': 'mail.mt_comment',
            'body': messages,
            # 'whatsapp_status': 'send',#BIAR GA MASUK SCHEDULER
            # 'whatsapp_number': sender_mobile,
        }
        if attachments:
            # if message_type == 'mp3':
            #     kwargs['voice'] = 'true'
            kwargs['attachments'] = attachments
        # if message_type == 'text':
        #     kwargs['body'] = plaintext2html(messages['text']['body'])
        # elif message_type == 'button':
        #     kwargs['body'] = messages['button']['text']
        # elif message_type in ('document', 'image', 'audio', 'video', 'sticker'):
        #     filename = messages[message_type].get('filename')
        #     mime_type = messages[message_type].get('mime_type')
        #     caption = messages[message_type].get('caption')
        #     datas = wa_api._get_whatsapp_document(messages[message_type]['id'])
        #     if not filename:
        #         extension = mimetypes.guess_extension(mime_type) or ''
        #         filename = message_type + extension
        #     kwargs['attachments'] = [(filename, datas)]
        #     if caption:
        #         kwargs['body'] = plaintext2html(caption)
        # elif message_type == 'location':
        #     url = Markup("https://maps.google.com/maps?q={latitude},{longitude}").format(
        #         latitude=messages['location']['latitude'], longitude=messages['location']['longitude'])
        #     body = Markup('<a target="_blank" href="{url}"> <i class="fa fa-map-marker"/> {location_string} </a>').format(
        #         url=url, location_string=_("Location"))
        #     if messages['location'].get('name'):
        #         body += Markup("<br/>{location_name}").format(location_name=messages['location']['name'])
        #     if messages['location'].get('address'):
        #         body += Markup("<br/>{location_address}").format(location_name=messages['location']['address'])
        #     kwargs['body'] = body
        # elif message_type == 'contacts':
        #     body = ""
        #     for contact in messages['contacts']:
        #         body += Markup("<i class='fa fa-address-book'/> {contact_name} <br/>").format(
        #             contact_name=contact.get('name', {}).get('formatted_name', ''))
        #         for phone in contact.get('phones'):
        #             body += Markup("{phone_type}: {phone_number}<br/>").format(
        #                 phone_type=phone.get('type'), phone_number=phone.get('phone'))
        #     kwargs['body'] = body
        # elif message_type == 'reaction':
        #     msg_uid = messages['reaction'].get('message_id')
        #     whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', msg_uid)])
        #     if whatsapp_message:
        #         partner_id = channel.whatsapp_partner_id
        #         emoji = messages['reaction'].get('emoji')
        #         whatsapp_message.mail_message_id._post_whatsapp_reaction(reaction_content=emoji, partner_id=partner_id)
        #         continue
        # else:
        #     _logger.warning("Unsupported whatsapp message type: %s", messages)
        #     continue
        # print ('==kwargs==',attachments,partners_to_notify)
        # if partners_to_notify == channel.whatsapp_partner_id and self.notify_user_ids.partner_id:
        #     partners_to_notify += self.notify_user_ids.partner_id
        # print ('==channel==',channel)
        # channel.channel_member_ids = [Command.clear()] + [Command.create({'partner_id': partner.id}) for partner in partners_to_notify]
        # channel._broadcast(partners_to_notify.ids)
        message = channel.message_post(message_type='whatsapp', **kwargs)
        #print ('==message===',message_type,message,message.attachment_ids)
        # self.env['discuss.voice.metadata'].create({
        #     'attachment_id': attachment.id,
        #     'duration': 0,  # You can set the actual duration if available
        #     'format': 'mp3' # Indicate the format if necessary
        # })
        if 'audio/mpeg' in message.attachment_ids.mapped('mimetype'):
            self.env['discuss.voice.metadata'].sudo().create({'attachment_id': message.attachment_ids.id})
        # if attachment:
        #     message.write({'attachment_ids': [attachment.id]})
        #     attachment.write({'res_model': 'discuss.channel', 'res_id': channel.id})
        # channel.message_post(message_type='whatsapp', **kwargs)#, body=messages, record_name=sender_name)
        return channel

    def _get_wgapi_client(self):
        """Get WGApi client instance"""
        _logger.info(f"Creating WGApi client for session: {self.session_name}, gateway: {self.gateway_url}")
        return WGApi(
            gateway_url=self.gateway_url,
            session_name=self.session_name,
            client_secret=self.client_secret,
            server=self,
        )

    # def action_get_qr_code(self):
    #     """Get QR code from gateway and store it"""
    #     self.ensure_one()
    #     client = self._get_wgapi_client()
    #     try:
    #         _logger.info(f"[action_get_qr_code] Requesting QR code for session: {self.session_name}")
    #         result = client.get_qr_code()
    #         _logger.info(f"[action_get_qr_code] QR code response: {result}")
    #         if result and (result.get('qr') or result.get('qrCode')):
    #             qr_val = result.get('qr') or result.get('qrCode')
    #             self.write({
    #                 'qr_scan': qr_val,
    #                 'connection_status': 'connecting'
    #             })
    #         return True
    #     except Exception as e:
    #         _logger.error(f"[action_get_qr_code] Error: {e}")
    #         raise UserError(_("Could not get QR code: %s") % str(e))


    def action_get_qr_code(self):
        """Get QR code from gateway and open modal for scanning"""
        self.ensure_one()
        client = self._get_wgapi_client()
        try:
            _logger.info(f"[action_get_qr_code] Requesting QR code for session: {self.session_name}")
            result = client.get_qr_code()
            _logger.info(f"[action_get_qr_code] QR code response: {result}")
            if result and (result.get('qr') or result.get('qrCode')):
                qr_val = result.get('qr') or result.get('qrCode')
                self.write({
                    'qr_scan': qr_val,
                    'connection_status': 'connecting'
                })
                # Prepare qr_scan for wizard (strip data:image/png;base64, if present)
                if qr_val.startswith('data:image/png;base64,'):
                    qr_scan_val = qr_val.split('data:image/png;base64,')[1]
                else:
                    qr_scan_val = False
                # Always update or create the wizard for this server
                wizard = self.env['whatsapp.qr.wizard'].sudo().search([
                    ('whatsapp_server_id', '=', self.id)
                ], order='id desc', limit=1)
                if wizard:
                    wizard.write({
                        'qr_code': qr_val,
                        'qr_scan': qr_scan_val,
                        'status': 'got qr code',
                    })
                else:
                    wizard = self.env['whatsapp.qr.wizard'].sudo().create({
                        'whatsapp_server_id': self.id,
                        'qr_code': qr_val,
                        'qr_scan': qr_scan_val,
                        'status': 'got qr code',
                    })
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Scan QR Code'),
                    'res_model': 'whatsapp.qr.wizard',
                    'view_mode': 'form',
                    'view_id': self.env.ref('custom_whatsapp.view_whatsapp_qr_wizard_form').id,
                    'res_id': wizard.id,
                    'target': 'new',
                }
            elif result and result.get('status') == 'connected':
                self.write({
                    'connection_status': 'connected',
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
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'Unknown error'
                _logger.error(f"[action_get_qr_code] No QR code or error: {result}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Could not get QR code: %s') % error_msg,
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"[action_get_qr_code] Error: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Could not get QR code: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_check_connection(self):
        """Check WhatsApp connection status and display notification"""
        self.ensure_one()
        client = self._get_wgapi_client()
        try:
            _logger.info(f"[action_check_connection] Checking connection for session: {self.session_name}")
            result = client.auth()
            _logger.info(f"[action_check_connection] Auth response: {result}")
            if result and result.get('status') == 'connected':
                self.write({
                    'connection_status': 'connected',
                    'qr_scan': False  # Clear QR code once connected
                })
                notif_type = 'success'
                notif_msg = _('Device is connected.')
            else:
                self.write({'connection_status': 'disconnected'})
                notif_type = 'danger'
                notif_msg = _('Device is not connected.')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Connection'),
                    'message': notif_msg,
                    'type': notif_type,
                    'sticky': notif_type == 'danger',
                }
            }
        except Exception as e:
            _logger.error(f"[action_check_connection] Error: {e}")
            self.write({'connection_status': 'disconnected'})
            clean_msg = self._clean_html_error(str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Connection'),
                    'message': _('Connection check failed: %s') % clean_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_disconnect(self):
        """Disconnect WhatsApp session"""
        self.ensure_one()
        client = self._get_wgapi_client()
        try:
            _logger.info(f"[action_disconnect] Logging out session: {self.session_name}")
            client.logout()
            self.write({
                'connection_status': 'disconnected',
                'qr_scan': False
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Disconnected from WhatsApp successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"[action_disconnect] Error: {e}")
            clean_msg = self._clean_html_error(str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Could not disconnect: %s') % clean_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _clean_html_error(self, msg):
        """Remove HTML tags and keep only text for error display."""
        if not msg:
            return msg
        # Remove HTML tags
        clean = re.sub('<[^<]+?>', '', msg)
        # Remove excessive whitespace and newlines
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Optionally, truncate if too long
        if len(clean) > 500:
            clean = clean[:500] + '...'
        return clean

    def notify_connection_status(self, status, message=None):
        """Display connection status notification from webhook or other events."""
        notif_type = 'success' if status == 'connected' else 'warning' if status == 'connecting' else 'danger'
        notif_title = _('WhatsApp Connection')
        notif_msg = message or _('Status: %s') % status
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': notif_title,
                'message': notif_msg,
                'type': notif_type,
                'sticky': notif_type == 'danger',
            }
        }

    def notify_batch_sms_result(self, result):
        """Display SMS batch delivery result as notification."""
        notif_type = 'success' if result.get('success') else 'danger'
        notif_title = _('SMS Delivery Result')
        notif_msg = result.get('message', _('Batch delivery completed.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': notif_title,
                'message': notif_msg,
                'type': notif_type,
                'sticky': notif_type == 'danger',
            }
        }

    def notify_send_message_result(self, success, message=None):
        """Display WhatsApp send message result as notification."""
        notif_type = 'success' if success else 'danger'
        notif_title = _('WhatsApp Message')
        notif_msg = message or (_('Message sent successfully.') if success else _('Failed to send message.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': notif_title,
                'message': notif_msg,
                'type': notif_type,
                'sticky': notif_type == 'danger',
            }
        }