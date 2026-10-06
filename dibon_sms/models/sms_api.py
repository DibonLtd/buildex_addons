import logging
import json

from odoo import fields
from odoo.addons.sms.tools.sms_api import SmsApi as BaseSmsApi

_logger = logging.getLogger(__name__)


class SmsApi(BaseSmsApi):
    def _contact_iap(self, local_endpoint, params, timeout=15):
        # Get default enabled provider
        IAPAccount = self.env["iap.account"].sudo()
        provider = IAPAccount.get_default_account()
        
        if not provider:
            _logger.error("No default SMS provider configured or enabled")
            return [{
                "state": "server_error",
                "uuid": number["uuid"],
                "error": "No default SMS provider configured"
            } for message in params["messages"] for number in message["numbers"]]
        
        res = []
        for message in params["messages"]:
            for number in message["numbers"]:
                res_value = {"state": "success", "uuid": number["uuid"]}
                try:
                    # Get the SMS record to determine the message type
                    sms = self.env["sms.sms"].sudo().search([("uuid", "=", number["uuid"])])
                    
                    # Get message_type from SMS record or use default
                    message_type = getattr(sms, 'message_type', 2)
                    
                    # Send SMS with message type
                    response = provider.send_sms(
                        number["number"], 
                        message["content"],
                        message_type=message_type
                    )

                    if not response or response.get("status") != 200:
                        res_value["state"] = "server_error"
                        res_value["error"] = response.get("message", "Unknown error")
                        _logger.error(f"SMS sending failed: {res_value['error']}")
                    elif response.get("status") == 200:
                        # Update SMS record with provider info and success status
                        if sms:
                            response_data = response.get("data", {})
                            api_status = response_data.get("status")
                            # delivery_status reflects gateway-level state; use values accepted by sms.sms
                            # allowed values: 'scheduled', 'sent', 'delivered', 'failed'
                            delivery_state = 'sent' if api_status == 'SUCCESS' else 'failed'
                            odoo_state = 'sent' if api_status == 'SUCCESS' else 'error'

                            vals = {
                                "provider_id": provider.id,
                                "state": odoo_state,
                                "message_id": response_data.get("msgId"),
                                "mnc": response_data.get("mnc"),
                                "mcc": response_data.get("mcc"),
                                "cost": response_data.get("cost"),
                                "api_response": str(response_data),
                                "gateway_status": response_data.get("status"),
                                "gateway_code": response_data.get("statusCode"),
                                "delivery_status": delivery_state,
                                "sent_date": fields.Datetime.now()
                            }
                            
                            if api_status != "SUCCESS":
                                vals["error"] = response_data.get("desc", "Unknown error")
                            
                            _logger.info(f"Updating SMS record {sms.id} with values: {vals}")
                            sms.write(vals)
                            # Create a structured API response record for auditing
                            try:
                                resp_model = self.env['dibon.sms_api_response']
                                resp_vals = {
                                    'sms_id': sms.id,
                                    'provider_id': provider.id,
                                    'status': response_data.get('status'),
                                    'status_code': response_data.get('statusCode'),
                                    'response_raw': str(response_data),
                                }
                                resp_model.sudo().create(resp_vals)
                            except Exception:
                                _logger.exception('Failed to create structured API response record')
                            # Post a single concise message on the sms record (avoid posting raw API JSON to chatter
                            # and avoid duplicating messages on partner and sms). The structured response is stored
                            # in `dibon.sms_api_response` for auditing and backfill.
                            try:
                                status = response_data.get('status')
                                code = response_data.get('statusCode')
                                desc = response_data.get('desc') or ''
                                msg = f"SMS sent to {sms.number} via {provider.sms_provider} - Gateway status: {status} ({code})"
                                if status != 'SUCCESS':
                                    # Add concise error text for failed sends
                                    msg = f"{msg} - Error: {desc}"
                                # Create a mail.message record directly (sms.sms may not have mail.thread)
                                try:
                                    subtype = self.env.ref('mail.mt_note').sudo()
                                    self.env['mail.message'].sudo().create({
                                        'subject': 'SMS delivery report',
                                        'body': msg,
                                        'message_type': 'notification',
                                        'subtype_id': subtype.id,
                                        'model': 'sms.sms',
                                        'res_id': sms.id,
                                    })
                                except Exception:
                                    # Fallback: log if mail.message could not be created
                                    _logger.exception('Failed to create mail.message for sms record')
                            except Exception:
                                _logger.exception("Failed to prepare concise API response for sms chatter")
                            # Force recompute provider stats
                            if provider:
                                provider.invalidate_recordset(['messages_sent', 'success_rate', 'total_cost', 'failed_count'])
                                provider._compute_message_stats()
                            # Mark the per-message result according to gateway status so the sms pipeline
                            # updates the sms state correctly. If gateway reports non-SUCCESS, mark as server_error
                            try:
                                if api_status == 'SUCCESS':
                                    res_value['state'] = 'success'
                                else:
                                    res_value['state'] = 'server_error'
                                    res_value['error'] = response_data.get('desc', 'Gateway reported failure')
                            except Exception:
                                # Leave default success state if anything unexpected
                                _logger.exception('Failed to set result state from gateway response')
                except Exception as e:
                    _logger.error("SMS sending failed: %s", str(e))
                    res_value["state"] = "server_error"
                    res_value["error"] = str(e)
                res.append(res_value)
        return res
