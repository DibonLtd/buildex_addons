import logging
import requests
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class IapAccount(models.Model):
    _inherit = "iap.account"

    sms_provider = fields.Selection(
        [("Dibon", "SMS Dibon"), ("4pay", "SMS 4Pay"), ("wapi", "SMS Wapi")], 
        string="SMS Provider", required=True, default="Dibon"
    )
    sms_secret = fields.Char(string="API Key")
    sms_gateway = fields.Char(string="SENDERS ID")
    is_default_provider = fields.Boolean(
        string="Is Default Provider", 
        default=False,
        help="Check this box to make this the default SMS provider"
    )
    state = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
        ('unregistered', 'Unregistered')
    ], string='Status', required=True, default='enabled',
        help="Whether this provider is enabled and can be used for sending SMS")
    description = fields.Text(string="Description",
        help="Additional notes about this provider configuration")
    balance = fields.Float(string="Balance", digits=(16, 2), readonly=True, 
        default=0.0, help="Current balance in the provider account",
        groups="base.group_system")
    balance_string = fields.Char(string="Balance Display", compute="_compute_balance_string", store=True,
        help="Balance with currency for display purposes")
    currency = fields.Char(string="Currency", default="KES", readonly=True,
        help="Currency of the balance")
    
    def _extract_numeric_balance(self, balance_str):
        """Extract numeric value from balance string"""
        try:
            # Remove currency code and 'Credits' if present
            cleaned = balance_str.replace('Credits', '').replace('KES', '').strip()
            # Convert to float
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    messages_sent = fields.Integer(string="Messages Sent", compute="_compute_message_stats", store=True,
        help="Total number of messages sent through this provider")
    success_rate = fields.Float(string="Success Rate", compute="_compute_message_stats", store=True,
        help="Percentage of successfully delivered messages")
    total_cost = fields.Char(string="Total Cost", compute="_compute_message_stats", store=True,
        help="Total cost of messages sent through this provider")
    failed_count = fields.Integer(string="Failed Messages", compute="_compute_message_stats", store=True,
        help="Number of failed message deliveries")
    sms_ids = fields.One2many('sms.sms', 'provider_id', string='SMS Messages', readonly=True)

    def _compute_balance_string(self):
        """Format balance with currency for display"""
        for record in self:
            try:
                _logger.info(f"Computing balance string for provider: {record.name}")
                balance = float(record.balance or 0.0)
                _logger.info(f"Current balance: {balance} {record.currency}")
                record.balance_string = f"{record.currency} {balance:,.2f}"
                _logger.info(f"Formatted balance: {record.balance_string}")
            except (ValueError, TypeError) as e:
                _logger.error(f"Error computing balance string: {str(e)}")
                record.balance_string = f"{record.currency} 0.00"

    @api.model
    def _extract_balance(self, balance_str):
        """Extract numeric balance from string like 'KES 10.0' or '10.0 Credits'"""
        if not balance_str:
            return 0.0
        # Handle both numeric and string inputs
        if isinstance(balance_str, (int, float)):
            return float(balance_str)
        try:
            # Remove currency and any other non-numeric chars except decimal point
            numeric_str = ''.join(c for c in str(balance_str) if c.isdigit() or c == '.')
            return float(numeric_str or '0.0')
        except (ValueError, TypeError):
            return 0.0

    def write(self, vals):
        """Write method with balance handling"""
        if 'balance' in vals and isinstance(vals['balance'], str):
            # Convert string balance to float
            vals['balance'] = self._extract_numeric_balance(vals['balance'])
        # Update last_balance_update when balance changes
        if 'balance' in vals:
            vals['last_balance_update'] = fields.Datetime.now()
        result = super().write(vals)
        if 'balance' in vals:
            self._compute_balance_string()
        return result
    sms_ids = fields.One2many('sms.sms', 'provider_id', string='SMS Messages')
    message_count = fields.Integer(string="Message Count", compute="_compute_message_count")

    def _compute_message_count(self):
        """Compute the total number of messages for this provider"""
        for record in self:
            record.message_count = len(record.sms_ids)

    @api.depends('sms_ids', 'sms_ids.state', 'sms_ids.delivery_status', 'sms_ids.cost')
    def _compute_message_stats(self):
        """Compute message statistics including sent, delivered, failed counts and costs"""
        for record in self:
            _logger.info(f"Computing message stats for provider: {record.name}")
            
            # Get all SMS messages for this provider
            sms_messages = record.sms_ids.sudo()
            _logger.info(f"Found {len(sms_messages)} total messages")
            
            # Basic counts with detailed logging
            total = len(sms_messages)
            # Consider both 'sent' state and 'delivered' status as successful
            successful = len(sms_messages.filtered(lambda m: m.state == 'sent' or m.delivery_status in ['sent', 'delivered']))
            failed = len(sms_messages.filtered(lambda m: m.state == 'error' or m.delivery_status == 'failed'))
            
            _logger.info(f"Message counts - Total: {total}, Successful: {successful}, Failed: {failed}")
            
            # Cost calculation with detailed logging
            total_cost = 0.0
            for msg in sms_messages:
                _logger.debug(f"Processing message {msg.id} - Cost: {msg.cost}, State: {msg.state}, "
                            f"Delivery Status: {msg.delivery_status}, API Response: {msg.api_response}")
                if msg.cost:
                    try:
                        cost_parts = msg.cost.split()
                        if len(cost_parts) >= 2:
                            msg_cost = float(cost_parts[1])
                            total_cost += msg_cost
                            _logger.debug(f"Added cost {msg_cost} to total")
                    except (ValueError, IndexError) as e:
                        _logger.warning(f"Could not parse cost value: {msg.cost} - Error: {str(e)}")
            
            # Calculate success rate considering sent messages as successful
            success_rate = (successful / total * 100) if total > 0 else 0
            _logger.info(f"Final calculations - Success Rate: {success_rate:.2f}%, "
                        f"Total Cost: {record.currency} {total_cost:.2f}")
            
            # Update computed fields
            record.messages_sent = total
            record.success_rate = success_rate
            record.failed_count = failed
            record.total_cost = f"{record.currency} {total_cost:.2f}"
            
            _logger.info("Stats computation completed")
            _logger.info(f"Updated stats - Messages Sent: {record.messages_sent}, "
                        f"Success Rate: {record.success_rate:.2f}%, "
                        f"Failed: {record.failed_count}, "
                        f"Total Cost: {record.total_cost}")
    last_balance_update = fields.Datetime(string="Last Balance Update", readonly=True)
    
    def _compute_success_rate(self):
        for record in self:
            if record.messages_sent > 0:
                success_count = self.env['sms.sms'].search_count([
                    ('provider_id', '=', record.id),
                    ('state', '=', 'sent')
                ])
                record.success_rate = (success_count / record.messages_sent) * 100
            else:
                record.success_rate = 0

    @api.model
    def get_default_account(self):
        """Get the default SMS account that is enabled"""
        default = self.search([
            ('is_default_provider', '=', True),
            ('state', '=', 'enabled')
        ], limit=1)
        if not default:
            default = self.search([('state', '=', 'enabled')], limit=1)
        return default

    def action_set_default(self):
        """Set this account as default"""
        self.ensure_one()
        if self.state != 'enabled':
            self.action_enable()
        self.env['iap.account'].search([('id', '!=', self.id)]).write({'is_default_provider': False})
        self.write({'is_default_provider': True})
        return True

    def action_enable(self):
        """Enable the provider"""
        self.ensure_one()
        self.write({'state': 'enabled'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_disable(self):
        """Disable the provider"""
        self.ensure_one()
        if self.is_default_provider:
            return {
                'warning': {
                    'title': 'Warning',
                    'message': 'Cannot disable the default provider. Please set another provider as default first.'
                }
            }
        self.write({'state': 'disabled'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def _get_service_from_provider(self):
        """Get or create the SMS service"""
        IAPService = self.env['iap.service'].sudo()
        service = IAPService.search([('technical_name', '=', 'sms.sms')], limit=1)
        if not service:
            service = IAPService.create({
                'name': 'SMS Service',
                'technical_name': 'sms.sms',
                'description': 'Service for sending SMS',
                'unit_name': 'Credits',
                'integer_balance': 0
            })
        return service

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure SMS service is set on creation"""
        service = self._get_service_from_provider()
        existing_providers = self.search_count([('service_id.technical_name', '=', 'sms.sms')])

        records = []
        for vals in vals_list:
            # Set service_id if not provided
            if service and not vals.get('service_id'):
                vals['service_id'] = service.id

            # If this is the first provider, make it default and enabled
            if not existing_providers:
                vals.update({
                    'is_default_provider': True,
                    'state': 'enabled'
                })
            existing_providers += 1

            records.append(vals)

        return super().create(records)

    message_ids = fields.One2many('sms.sms', 'provider_id', string='Messages')

    def action_view_messages(self):
        """Open the SMS messages view filtered by this provider"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sms.sms_sms_action")
        action['domain'] = [('provider_id', '=', self.id)]
        action['context'] = {'default_provider_id': self.id}
        return action

    def action_refresh_stats(self):
        """Refresh message statistics"""
        self.ensure_one()
        _logger.info(f"Refreshing stats for provider: {self.name}")
        # Force recompute of all stats
        self.invalidate_recordset(['messages_sent', 'success_rate', 'total_cost', 'failed_count'])
        self._compute_message_stats()
        # Make sure changes are immediately visible
        self.env.cr.commit()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def send_sms(self, number, message):
        """Send SMS using this provider configuration"""
        self.ensure_one()
        
        if self.state != 'enabled':
            return {
                'status': 400,
                'message': 'Provider is not enabled'
            }

        if not self.sms_gateway or not self.sms_secret:
            return {
                'status': 400,
                'message': 'Provider configuration is incomplete'
            }

        try:
            # Here implement the actual SMS sending logic based on provider
            if self.sms_provider == 'Dibon':
                # Log the sending attempt
                _logger.info("Sending SMS to %s using provider %s", number, self.name)
                _logger.info("Message content: %s", message)
                _logger.info("Preparing to send SMS via Dibon")
                
                # Prepare request
                headers = {
                    'Authorization': f'Bearer {self.sms_secret}',
                    'Content-Type': 'application/json'
                }
                # Prepare request data
                data = {
                    'from': 'DIBON',
                    'to': number,
                    'message': message,
                    'message_type': 2  # Standard message type
                }
                
                # Log request details
                _logger.info("Dibon SMS Request - Endpoint: %s", self.sms_gateway)
                _logger.info("Dibon SMS Request - Headers: %s", headers)
                _logger.info("Dibon SMS Request - Data: %s", data)
                
                _logger.info("Sending request to Dibon API...")
                response = requests.post(self.sms_gateway, json=data, headers=headers)
                
                # Log response
                _logger.info("Dibon API Response Status Code: %s", response.status_code)
                _logger.info("Dibon API Raw Response: %s", response.text)
                
                if response.status_code == 200:
                    result = response.json()
                    _logger.info("Dibon API Success Response: %s", result)
                    
                    # Update balance and track message info
                    if 'balance' in result:
                        balance_str = result.get('balance', '0.0')
                        balance = self._extract_balance(balance_str)
                        _logger.info("Converting balance '%s' to numeric value: %s", balance_str, balance)
                        
                        vals = {
                            'balance': balance,
                            'last_balance_update': fields.Datetime.now(),
                            'messages_sent': self.messages_sent + 1
                        }
                        
                        # Find any pending SMS messages
                        SmsSms = self.env['sms.sms'].sudo()
                        sms = SmsSms.search([
                            ('number', '=', number),
                            ('state', 'in', ['outgoing', 'pending']),
                            ('body', '=', message)
                        ], limit=1)
                        
                        if sms and result.get('msgId'):
                            sms.write({
                                'message_id': result['msgId'],
                                'delivery_status': 'scheduled',
                                'state': 'sent',
                                'error': False
                            })
                        
                        self.write(vals)
                        _logger.info("Updating IAP account balance to: %s", balance)
                    
                    return {
                        'status': 200,
                        'message': 'Message has been queued for sending!',
                        'data': result
                    }
                
                return {
                    'status': response.status_code,
                    'message': response.text
                }
                
            elif self.sms_provider == '4pay':
                # 4Pay implementation
                return {
                    'status': 200,
                    'message': 'SMS sent successfully'
                }
            elif self.sms_provider == 'wapi':
                # Wapi implementation
                return {
                    'status': 200,
                    'message': 'SMS sent successfully'
                }
            else:
                return {
                    'status': 400,
                    'message': f'Provider {self.sms_provider} not supported'
                }
        except Exception as e:
            _logger.error("SMS sending failed: %s", str(e))
            return {
                'status': 500,
                'message': str(e)
            }

    @api.model
    def action_view_settings(self):
        """Smart button to view/create SMS settings"""
        # Always get the service first
        service = self._get_service_from_provider()

        # Search for any providers with the SMS service
        providers = self.search([('service_id.technical_name', '=', 'sms.sms')])

        action = self.env.ref('dibon_sms.action_dibon_sms_settings').read()[0]

        # Always use list view if providers exist
        if providers:
            action.update({
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
                'domain': [('service_id.technical_name', '=', 'sms.sms')],
                'context': {'default_service_id': service.id}
            })
        else:
            # Create mode if no providers
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {
                    'default_service_id': service.id,
                    'default_name': 'Dibon SMS',
                    'default_sms_provider': 'Dibon',
                    'default_state': 'enabled',
                    'default_is_default_provider': True
                }
            })
        return action

    @api.model
    def _init_sms_service(self):
        """Initialize SMS service if it doesn't exist"""
        service = self._get_service_from_provider()
        
        # Update existing SMS accounts to use this service
        sms_accounts = self.search([
            '|',
            ('sms_provider', '!=', False),
            ('service_id.technical_name', '=', 'sms.sms')
        ])
        
        if sms_accounts:
            sms_accounts.write({
                'service_id': service.id,
                'service_name': 'sms'
            })
            
            # Ensure at least one default provider
            default_exists = self.search_count([
                ('service_id.technical_name', '=', 'sms.sms'),
                ('is_default_provider', '=', True)
            ])
            if not default_exists:
                sms_accounts[0].action_set_default()
                
        return True
    sms_secret = fields.Char(string="API Key")
    sms_gateway = fields.Char(string="SENDERS ID")

    def send_sms(self, phone_number, message, message_type=2):
        """Send SMS using IAP
        
        Args:
            phone_number (str): The recipient's phone number
            message (str): The message content
            message_type (int, optional): Message type. Defaults to 2.
        """
        if self.state != 'enabled':
            _logger.error(f"Cannot send SMS: Provider {self.sms_provider} is not enabled")
            return {"status": 400, "message": f"SMS Provider {self.sms_provider} is not enabled", "data": False}
            
        _logger.info(f"Sending SMS to {phone_number} using provider {self.sms_provider}")
        _logger.info(f"Message content: {message}")
        _logger.info(f"Message type: {message_type}")
        
        response = {}
        try:
            if self.sms_provider == "Dibon":
                response = self._send_sms_dibon(phone_number, message, message_type)
            elif self.sms_provider == "4pay":
                response = self._send_sms_4pay(phone_number, message)
            elif self.sms_provider == "wapi":
                response = self._send_sms_wapi(phone_number, message)
            else:
                _logger.error(f"Unknown SMS provider: {self.sms_provider}")
                return {"status": 400, "message": f"Unknown SMS provider: {self.sms_provider}", "data": False}
                
            _logger.info(f"SMS sending completed. Response: {response}")
            return response
            
        except Exception as e:
            _logger.error(f"Exception while sending SMS: {str(e)}", exc_info=True)
            return {"status": 500, "message": str(e), "data": False}


    def _send_sms_dibon(self, phone_number, message, message_type=2):
        """Send SMS via Dibon API
        
        Args:
            phone_number (str): The recipient's phone number
            message (str): The message content
            message_type (int, optional): Message type. Defaults to 2.
        """
        _logger.info("Preparing to send SMS via Dibon")
        
        apikey = self.sms_secret
        endpoint = "https://sendsms.dibon.co.ke/api/messaging/sendsms"
        
        data = {
            "from": self.sms_gateway,
            "to": phone_number,
            "message": message,
            "message_type": message_type
        }

        headers = {
            "Authorization": f"Bearer {apikey}",
            "Content-Type": "application/json",
        }

        _logger.info(f"Dibon SMS Request - Endpoint: {endpoint}")
        _logger.info(f"Dibon SMS Request - Headers: {headers}")
        _logger.info(f"Dibon SMS Request - Data: {data}")

        try:
            _logger.info("Sending request to Dibon API...")
            response = requests.post(endpoint, json=data, headers=headers, timeout=60)
            _logger.info(f"Dibon API Response Status Code: {response.status_code}")
            _logger.info(f"Dibon API Raw Response: {response.text}")

            if response.status_code == 200:
                resp_json = response.json()
                _logger.info(f"Dibon API Success Response: {resp_json}")
                
                # Handle balance update if available
                balance = resp_json.get("balance")
                if balance is not None:
                    try:
                        # Extract numeric value from "KES X.Y" format
                        numeric_balance = float(balance.split()[1])
                        _logger.info(f"Converting balance '{balance}' to numeric value: {numeric_balance}")
                        
                        # Update the IAP account balance
                        _logger.info(f"Updating IAP account balance to: {numeric_balance}")
                        self.sudo().write({
                            "balance": numeric_balance,
                        })
                    except (IndexError, ValueError) as e:
                        _logger.error(f"Failed to parse balance '{balance}': {str(e)}")
                else:
                    _logger.info("No balance information in response")

                return {
                    "status": 200,
                    "message": "Message has been queued for sending!",
                    "data": resp_json,
                }
            else:
                _logger.error(f"Dibon API Error - Status Code: {response.status_code}")
                _logger.error(f"Dibon API Error Response: {response.text}")
                return {
                    "status": response.status_code,
                    "message": response.text,
                    "data": False,
                }

        except requests.exceptions.RequestException as e:
            _logger.error(f"Dibon API Request Failed: {str(e)}", exc_info=True)
            return {"status": 500, "message": str(e), "data": False}
        except Exception as e:
            _logger.error(f"Unexpected error while sending SMS via Dibon: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Unexpected error: {str(e)}", "data": False}


    def _send_sms_4pay(self, phone_number, message):
        _logger.info("Preparing to send SMS via 4Pay")
        
        params = {
            "servID": self.sms_gateway,
            "msg_dst": phone_number,
            "msg_text": message,
            "API": "",
            "password": self.sms_secret,
            "external_messageID": 1,
        }
        
        endpoint = "https://sms.4pay.ro/smscust/api.send_sms"
        _logger.info(f"4Pay SMS Request - Endpoint: {endpoint}")
        _logger.info(f"4Pay SMS Request - Parameters: {params}")
        
        try:
            _logger.info("Sending request to 4Pay API...")
            result = requests.get(endpoint, params=params, timeout=60)
            _logger.info(f"4Pay API Response Status Code: {result.status_code}")
            
            response = result.content.decode("utf-8")
            _logger.info(f"4Pay API Raw Response: {response}")

            if "OK" not in response:
                _logger.error(f"4Pay API Error Response: {response}")
                res = {"status": 500, "message": response, "data": False}
            else:
                _logger.info("4Pay SMS sent successfully")
                res = {"status": 200, "message": "Message has been queued for sending!", "data": False}

            return res
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"4Pay API Request Failed: {str(e)}", exc_info=True)
            return {"status": 500, "message": str(e), "data": False}
        except Exception as e:
            _logger.error(f"Unexpected error while sending SMS via 4Pay: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Unexpected error: {str(e)}", "data": False}

    def _send_sms_wapi(self, phone_number, message):
        _logger.info("Preparing to send SMS via Wapi")
        
        # Define the endpoint and payload
        url = "https://smswapi.com/api/send/sms"
        _logger.info(f"Wapi SMS Request - Endpoint: {url}")
        
        data = {
            "secret": self.sms_secret,
            "mode": "devices",
            "phone": phone_number,
            "message": message,
            "device": self.sms_gateway,
            "sim": 1,
        }
        
        _logger.info(f"Wapi SMS Request - Data: {data}")

        try:
            _logger.info("Sending request to Wapi API...")
            response = requests.post(url, data=data, timeout=60)
            _logger.info(f"Wapi API Response Status Code: {response.status_code}")
            _logger.info(f"Wapi API Raw Response: {response.text}")

            if response.status_code == 200:
                resp_json = response.json()
                _logger.info(f"Wapi API Success Response: {resp_json}")
                return {
                    "status": 200,
                    "message": "Message has been queued for sending!",
                    "data": resp_json
                }
            else:
                _logger.error(f"Wapi API Error - Status Code: {response.status_code}")
                _logger.error(f"Wapi API Error Response: {response.text}")
                return {
                    "status": response.status_code,
                    "message": response.content.decode('utf-8'),
                    "data": False
                }

        except requests.exceptions.RequestException as e:
            _logger.error(f"Wapi API Request Failed: {str(e)}", exc_info=True)
            return {"status": 500, "message": str(e), "data": False}
        except Exception as e:
            _logger.error(f"Unexpected error while sending SMS via Wapi: {str(e)}", exc_info=True)
            return {"status": 500, "message": f"Unexpected error: {str(e)}", "data": False}
