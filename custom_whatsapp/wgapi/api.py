from odoo import _
import warnings
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Response
import json
import re
import ast
import requests
import html2text
import datetime

class WGApi(object):
    def __init__(self, gateway_url, session_name, client_secret=None, server=None, **kwargs):
        self.gateway_url = gateway_url or 'http://localhost:5001'
        self.session_name = session_name
        self.client_secret = client_secret
        self.headers = {'Content-Type': 'application/json'}
        self.server = server
            
    def auth(self):
        """Get session status from stored connection status."""
        # Return stored connection status from database
        return {
            'status': self.server.connection_status or 'disconnected'
        }
    
    def logout(self):
        """Logout and clear session"""
        import logging
        _logger = logging.getLogger(__name__)
        
        if not self.session_name:
            _logger.error('[WGApi.logout] No active session to logout')
            raise UserError(_('No active session to logout'))
            
        url = f"{self.gateway_url}/session/logout"
        params = {'session': self.session_name}
        
        _logger.info('[WGApi.logout] Attempting to logout session: %s', self.session_name)
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            _logger.info('[WGApi.logout] Response status: %s', response.status_code)
            
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    error_msg = response.text or error_msg
                
                _logger.error('[WGApi.logout] Logout failed: %s', error_msg)
                raise UserError(_('Failed to logout: %s') % error_msg)
            
            try:
                result = response.json()
                _logger.info('[WGApi.logout] Logout result: %s', result)
                return result
            except json.JSONDecodeError as je:
                _logger.error('[WGApi.logout] Invalid response format: %s', je)
                raise UserError(_('Invalid response from WhatsApp Gateway'))
                
        except requests.exceptions.Timeout:
            _logger.error('[WGApi.logout] Request timeout')
            raise UserError(_('Timeout while logging out'))
            
        except requests.exceptions.RequestException as re:
            _logger.error('[WGApi.logout] Request error: %s', re)
            raise UserError(_('Error during logout: %s') % str(re))
    def send_document(self, phone, caption, document_url, document_name, is_group=False):
        """Send a document with caption"""
        import logging
        _logger = logging.getLogger(__name__)
        
        if not phone or not document_url:
            _logger.error('[WGApi.send_document] Missing required parameters - phone: %s, document_url: %s',
                         phone, document_url)
            raise UserError(_('Phone number and document URL are required'))
            
        # Defensive: refuse to send if phone is invalid
        if not phone or phone == '0' or not str(phone).isdigit() or len(str(phone)) < 8:
            _logger.warning('[WGApi.send_document] Refusing to send: invalid WhatsApp number: %s', phone)
            return {'status': 'error', 'message': 'Invalid WhatsApp number, not sent to gateway'}
        
        url = f"{self.gateway_url}/message/send-document"
        data = {
            'session': self.session_name,
            'to': phone,
            'text': caption or '',
            'document_url': document_url,
            'document_name': document_name or 'document',
            'is_group': is_group
        }
        
        _logger.info('[WGApi.send_document] Sending document - URL: %s, Phone: %s, Document: %s',
                     url, phone, document_url)
        
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            _logger.info('[WGApi.send_document] Response status: %s', response.status_code)
            
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    error_msg = response.text or error_msg
                
                _logger.error('[WGApi.send_document] Failed to send: %s', error_msg)
                raise UserError(_('Failed to send document: %s') % error_msg)
            
            try:
                result = response.json()
                _logger.info('[WGApi.send_document] Send result: %s', result)
                return result
            except json.JSONDecodeError as je:
                _logger.error('[WGApi.send_document] Invalid response format: %s', je)
                raise UserError(_('Invalid response from WhatsApp Gateway'))
                
        except requests.exceptions.Timeout:
            _logger.error('[WGApi.send_document] Request timeout')
            raise UserError(_('Timeout while sending document'))
            
        except requests.exceptions.RequestException as re:
            _logger.error('[WGApi.send_document] Request error: %s', re)
            raise UserError(_('Error sending document: %s') % str(re))
            # raise UserError(_('Error logging out: %s') % str(err))

    def get_qr_code(self):
        """Get session QR code for display in Odoo (using /session/start)"""
        import logging
        _logger = logging.getLogger(__name__)
        
        if not self.gateway_url or not self.session_name:
            _logger.error('[WGApi.get_qr_code] Invalid configuration - gateway_url: %s, session_name: %s',
                         self.gateway_url, self.session_name)
            raise UserError(_('Invalid WhatsApp configuration: Gateway URL and Session Name are required'))
            
        url = f"{self.gateway_url}/session/start"
        params = {'session': self.session_name}
        
        _logger.info('[WGApi.get_qr_code] Requesting QR code - URL: %s, Session: %s',
                     url, self.session_name)
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            _logger.info('[WGApi.get_qr_code] Response status: %s', response.status_code)
            
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    error_msg = response.text or error_msg
                
                _logger.error('[WGApi.get_qr_code] Failed to get QR code: %s', error_msg)
                raise UserError(_('Failed to get QR code: %s') % error_msg)
            
            try:
                data = response.json()
                _logger.info('[WGApi.get_qr_code] Response data received')
                
                if not isinstance(data, dict):
                    _logger.error('[WGApi.get_qr_code] Invalid response format: %s', data)
                    raise UserError(_('Invalid response format from WhatsApp Gateway'))
                
                # Accept both 'qrCode' and 'qr_code' and 'qr' for compatibility
                qr_val = data.get('qrCode') or data.get('qr_code') or data.get('qr')
                status = data.get('status')
                
                if not status:
                    _logger.error('[WGApi.get_qr_code] Missing status in response: %s', data)
                    raise UserError(_('Invalid response: missing status from WhatsApp Gateway'))
                
                result = {
                    'status': status,
                    'qrCode': qr_val,
                    'message': data.get('message', '')
                }
                
                _logger.info('[WGApi.get_qr_code] Successfully retrieved QR code. Status: %s', status)
                return result
                
            except json.JSONDecodeError as je:
                _logger.error('[WGApi.get_qr_code] Failed to parse response: %s', je)
                raise UserError(_('Invalid JSON response from WhatsApp Gateway'))
                
        except requests.exceptions.Timeout:
            _logger.error('[WGApi.get_qr_code] Request timeout')
            raise UserError(_('Timeout while getting QR code'))
            
        except requests.exceptions.RequestException as re:
            _logger.error('[WGApi.get_qr_code] Request error: %s', re)
            raise UserError(_('Error getting QR code: %s') % str(re))

    def send_message(self, phone, message, is_group=False):
        """Send a text message"""
        import logging
        _logger = logging.getLogger(__name__)
        
        if not phone or not message:
            _logger.error('[WGApi.send_message] Missing required parameters - phone: %s, message length: %s',
                         phone, len(message) if message else 0)
            raise UserError(_('Phone number and message are required'))
            
        # Defensive: refuse to send if phone is invalid
        if not phone or phone == '0' or not str(phone).isdigit() or len(str(phone)) < 8:
            _logger.warning('[WGApi.send_message] Refusing to send: invalid WhatsApp number: %s', phone)
            # return {'status': 'error', 'message': 'Invalid WhatsApp Number: %s, not sent to gateway' % phone}
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Send Error'),
                    'message': _('Invalid WhatsApp Number: %s, not sent to gateway') % phone,
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        url = f"{self.gateway_url}/message/send-text"
        data = {
            'session': self.session_name,
            'to': phone,
            'text': message,
            'is_group': is_group
        }
        
        _logger.info('[WGApi.send_message] Sending message - URL: %s, Phone: %s, Length: %d',
                     url, phone, len(message))
        
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            _logger.info('[WGApi.send_message] Response status: %s', response.status_code)
            
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    error_msg = response.text or error_msg
                
                _logger.error('[WGApi.send_message] Failed to send: %s', error_msg)
                raise UserError(_('Failed to send message: %s') % error_msg)
            
            try:
                result = response.json()
                _logger.info('[WGApi.send_message] Send result: %s', result)
                return result
            except json.JSONDecodeError as je:
                _logger.error('[WGApi.send_message] Invalid response format: %s', je)
                raise UserError(_('Invalid response from WhatsApp Gateway'))
                
        except requests.exceptions.Timeout:
            _logger.error('[WGApi.send_message] Request timeout')
            raise UserError(_('Timeout while sending message'))
            
        except requests.exceptions.RequestException as re:
            _logger.error('[WGApi.send_message] Request error: %s', re)
            raise UserError(_('Error sending message: %s') % str(re))

    def send_image(self, phone, caption, image_url, is_group=False):
        """Send an image with caption"""
        import logging
        _logger = logging.getLogger(__name__)
        
        if not phone or not image_url:
            _logger.error('[WGApi.send_image] Missing required parameters - phone: %s, image_url: %s',
                         phone, image_url)
            raise UserError(_('Phone number and image URL are required'))
            
        # Defensive: refuse to send if phone is invalid
        if not phone or phone == '0' or not str(phone).isdigit() or len(str(phone)) < 8:
            _logger.warning('[WGApi.send_image] Refusing to send: invalid WhatsApp number: %s', phone)
            return {'status': 'error', 'message': 'Invalid WhatsApp number, not sent to gateway'}
        
        url = f"{self.gateway_url}/message/send-image"
        data = {
            'session': self.session_name,
            'to': phone,
            'text': caption or '',
            'image_url': image_url,
            'is_group': is_group
        }
        
        _logger.info('[WGApi.send_image] Sending image - URL: %s, Phone: %s, Image: %s',
                     url, phone, image_url)
        
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            _logger.info('[WGApi.send_image] Response status: %s', response.status_code)
            
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    error_msg = response.text or error_msg
                
                _logger.error('[WGApi.send_image] Failed to send: %s', error_msg)
                raise UserError(_('Failed to send image: %s') % error_msg)
            
            try:
                result = response.json()
                _logger.info('[WGApi.send_image] Send result: %s', result)
                return result
            except json.JSONDecodeError as je:
                _logger.error('[WGApi.send_image] Invalid response format: %s', je)
                raise UserError(_('Invalid response from WhatsApp Gateway'))
                
        except requests.exceptions.Timeout:
            _logger.error('[WGApi.send_image] Request timeout')
            raise UserError(_('Timeout while sending image'))
            
        except requests.exceptions.RequestException as re:
            _logger.error('[WGApi.send_image] Request error: %s', re)
            raise UserError(_('Error sending image: %s') % str(re))
            return response.json()
        except requests.exceptions.RequestException as err:
            raise UserError(_('Error sending image: %s') % str(err))

    # def send_document(self, phone, caption, document_url, document_name, is_group=False):
    #     """Send a document with caption"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
    #     url = f"{self.gateway_url}/message/send-document"
    #     data = {
    #         'session': self.session_name,
    #         'to': phone,
    #         'text': caption,
    #         'document_url': document_url,
    #         'document_name': document_name,
    #         'is_group': is_group
    #     }
    #     _logger.info('[WGApi.send_document] POST %s with data: %s', url, data)
    #     try:
    #         response = requests.post(url, json=data, headers=self.headers)
    #         _logger.info('[WGApi.send_document] Response: %s', response.text)
    #         return response.json()
    #     except requests.exceptions.RequestException as err:
    #         _logger.error('[WGApi.send_document] Error: %s', err)
    #         raise UserError(_('Error sending document: %s') % str(err))
    def send_document(self, phone, caption, document_url, document_name, is_group=False):
            """Send a document with caption"""
            import logging
            _logger = logging.getLogger(__name__)
            
            if not phone or not document_url:
                _logger.error('[WGApi.send_document] Missing required parameters - phone: %s, document_url: %s',
                            phone, document_url)
                raise UserError(_('Phone number and document URL are required'))
                
            # Defensive: refuse to send if phone is invalid (for all message types)
            if not phone or phone == '0' or not str(phone).isdigit() or len(str(phone)) < 8:
                _logger.warning('[WGApi.send_document] Refusing to send: invalid WhatsApp number: %s', phone)
                return {'status': 'error', 'message': 'Invalid WhatsApp number, not sent to gateway'}
            
            url = f"{self.gateway_url}/message/send-document"
            data = {
                'session': self.session_name,
                'to': phone,
                'text': caption,
                'document_url': document_url,
                'document_name': document_name,
                'is_group': is_group
            }
            _logger.info('[WGApi.send_document] POST %s with data: %s', url, data)
            try:
                response = requests.post(url, json=data, headers=self.headers)
                _logger.info('[WGApi.send_document] Response: %s', response.text)
                return response.json()
            except requests.exceptions.RequestException as err:
                _logger.error('[WGApi.send_document] Error: %s', err)
                raise UserError(_('Error sending document: %s') % str(err))

    def get_count(self):
        data = {}
        url = self.APIUrl + 'count/' + self.dibon_key +'/' + self.dibon_secret
        data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        res = json.loads(data_req.text)
        #print ('===res===',res)
        return res.get('result') and res['result'] or {}
    
    def get_limit(self):
        data = {}
        url = self.APIUrl + 'limit/' + self.dibon_key +'/' + self.dibon_secret
        data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        res = json.loads(data_req.text)
        #print ('===res===',res)
        return res.get('result') and res['result'] or {}
    
    def get_number(self):
        data= {}
        url = self.APIUrl + 'check/' + self.dibon_key +'/' + self.dibon_secret
        data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        res = json.loads(data_req.text)
        # print ('===get_number===',res)
        return res.get('result') and res['result'] or {}
    
    def get_authenticate(self, data):
        # # url = self.APIUrl + 'get/' + self.dibon_key +'/' + self.dibon_secret + '/' + method
        # url = self.APIUrl + 'authentication'
        # data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        # # print ('--get_authenticate--',url,data_req,data)
        # res = json.loads(data_req.text)
        # return res.get('result') and res['result'] or {}
        try:
            #requests.get(self.APIUrl+'status/'+self.dibon_key+'/'+self.dibon_secret, headers={'Content-Type': 'application/json'})
            url = self.APIUrl + 'authentication'
            data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
            # print ('--get_authenticate--',url,data_req,data)
            res = json.loads(data_req.text)
            return res.get('result') and res['result'] or {}
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as err:
            raise warnings.warn(_('Error! Could not connect to Whatsapp account. %s')% (err))

    def get_qrcode(self, data):
        # url = self.APIUrl + 'get/' + self.dibon_key +'/' + self.dibon_secret + '/' + method
        url = self.APIUrl + '2.0/qr'
        data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        # print ('==get_qrcode==',url,data,data_req)
        res = json.loads(data_req.text)
        # print ('--get_qrcode--',data_req)
        return res.get('result') and res['result'] or {}

    # def get_request(self, method, data):
    #     # url = self.APIUrl + 'get/' + self.dibon_key +'/' + self.dibon_secret + '/' + method
    #     url = self.APIUrl + 'get/' + self.dibon_key +'/' + self.dibon_secret + '/' + method
    #     data_req = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
    #     print ('--get_request--',url,method,data)
    #     res = json.loads(data_req.text)
    #     return res.get('result') and res['result'] or {}

    def post_number(self, data):
        url = self.APIUrl + '2.0/number'
        payload = json.dumps(data)
        # print ('====token===',token)
        response = requests.post(url, data=payload, headers={'Content-Type': 'application/json'})
        # print ('===post_number==',response.text,url,payload)
        if response.status_code == 200:
            result = json.loads(response.text)
            # print ('===message1=',url,payload,result)
            message = result.get('result').get('message')
            # chatID = message.get('id').split('_')[1] if '_' in message.get('id') else message.get('id')
            return {'chatID': 1, 'message': message}
        else:
            return {'message': {'sent': False, 'message': 'Error'}}

    def get_request(self, token, data):
        # url = self.APIUrl + 'get/' + self.dibon_key +'/' + self.dibon_secret + '/' + method
        url = self.APIUrl + '2.0/get'
        payload = json.dumps(data)
        response = requests.get(url, data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token})
        result = json.loads(response.text)
        # print ('--get_request--',url,data,response.text)
        return result.get('result') and result['result'] or {}

    def post_request(self, token, data):
        url = self.APIUrl + '2.0/post'
        payload = json.dumps(data)
        # print ('====token===',token)
        response = requests.post(url, data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token})
        if response.status_code == 200:
            result = json.loads(response.text)
            # print ('===message1=',url,payload,result)
            message = result.get('result').get('message')
            # chatID = message.get('id').split('_')[1] if '_' in message.get('id') else message.get('id')
            return {'chatID': 1, 'message': message}
        else:
            return {'message': {'sent': False, 'message': 'Error'}}
    
    
    def get_phone(self, method, phone):
        data = {}
        url = self.APIUrl + 'phone/' + self.dibon_key + '/'+self.dibon_secret +'/'+ method + '/' + phone
        data = requests.get(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        res = json.loads(data.text)
        return res.get('result') and res['result'] or {}