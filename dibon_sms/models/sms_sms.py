import logging
import json
import ast

from werkzeug.urls import url_join

from odoo import models, fields, tools

from .sms_api import SmsApi

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = "sms.sms"

    provider_id = fields.Many2one('iap.account', string='Provider',
        domain="[('service_id.technical_name', '=', 'sms.sms')]",
        ondelete='set null',
        help="The provider that was used to send this message",
        index=True)
    
    message_id = fields.Char(string="Provider Message ID", 
        help="Message ID returned by the provider")
    
    delivery_status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed')
    ], string="Delivery Status", default='scheduled',
        help="Status of message delivery from the provider")
        
    error = fields.Text(string="Error Message",
        help="Error message if the sending failed")
        
    api_response = fields.Text(string="API Response",
        help="Raw API response from the provider")

    api_response_pretty = fields.Text(string="API Response (pretty)",
        compute="_compute_api_response_pretty", store=False)
        
    mnc = fields.Char(string="MNC",
        help="Mobile Network Code")
        
    mcc = fields.Char(string="MCC",
        help="Mobile Country Code")
        
    cost = fields.Char(string="Cost",
        help="Cost of sending the message")

    gateway_status = fields.Char(string="Gateway Status",
        help="Status string returned by the gateway (e.g., SUCCESS/FAILED)")

    gateway_code = fields.Char(string="Gateway Code",
        help="Numeric or status code returned by the gateway")

    message_type = fields.Integer(string="Message Type", 
        default=2,
        help="Type of message to send")
        
    auto_delete = fields.Boolean(string="Auto Delete", 
        default=False,
        help="If checked, successful messages will be deleted automatically")
        
    sent_date = fields.Datetime(string="Sent Date",
        help="Date and time when the message was sent")

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """Send SMS after checking the number (presence and formatting)."""
        # Override auto-deletion settings
        unlink_sent = False
        unlink_failed = False
        
        messages = [
            {
                "content": body,
                "numbers": [{"number": sms.number, "uuid": sms.uuid} for sms in body_sms_records],
            }
            for body, body_sms_records in self.grouped("body").items()
        ]

        delivery_reports_url = url_join(self[0].get_base_url(), "/sms/status")
        try:
            results = SmsApi(self.env)._send_sms_batch(messages, delivery_reports_url=delivery_reports_url)
        except Exception as e:
            _logger.info(
                "Sent batch %s SMS: %s: failed with exception %s",
                len(self.ids),
                self.ids,
                e,
            )
            if raise_exception:
                raise
            results = [{"uuid": sms.uuid, "state": "server_error"} for sms in self]
        else:
            # Log detailed information about each SMS
            for result in results:
                _logger.info(
                    "SMS Status - UUID: %s, State: %s, Details: %s",
                    result.get("uuid"),
                    result.get("state"),
                    result
                )
            
            _logger.info("Send batch %s SMS: %s: gave %s", len(self.ids), self.ids, results)

        results_uuids = [result["uuid"] for result in results]
        all_sms_sudo = (
            self.env["sms.sms"]
            .sudo()
            .search([("uuid", "in", results_uuids)])
            .with_context(sms_skip_msg_notification=True)
        )

        for iap_state, results_group in tools.groupby(results, key=lambda result: result["state"]):
            uuids = list(result["uuid"] for result in results_group)
            sms_sudo = all_sms_sudo.filtered(lambda s, list_uuids=list(uuids): s.uuid in list_uuids)
            if success_state := self.IAP_TO_SMS_STATE_SUCCESS.get(iap_state):
                sms_sudo.sms_tracker_id._action_update_from_sms_state(success_state)
                to_delete = {"to_delete": True} if unlink_sent else {}
                sms_sudo.write({"state": success_state, "failure_type": False, **to_delete})
            else:
                failure_type = self.IAP_TO_SMS_FAILURE_TYPE.get(iap_state, "unknown")
                # Log failure details
                _logger.info(
                    "SMS Failure - UUID: %s, Type: %s, IAP State: %s",
                    sms_sudo.uuid,
                    failure_type,
                    iap_state
                )
                
                if failure_type != "unknown":
                    sms_sudo.sms_tracker_id._action_update_from_sms_state("error", failure_type=failure_type)
                else:
                    sms_sudo.sms_tracker_id._action_update_from_provider_error(iap_state)
                to_delete = {"to_delete": True} if unlink_failed else {}
                sms_sudo.write({"state": "error", "failure_type": failure_type, **to_delete})

        all_sms_sudo.mail_message_id._notify_message_notification_update()

    def _compute_api_response_pretty(self):
        for sms in self:
            raw = sms.api_response
            pretty = ''
            if not raw:
                sms.api_response_pretty = ''
                continue
            # Try parse as JSON
            try:
                parsed = json.loads(raw)
            except Exception:
                try:
                    parsed = ast.literal_eval(raw)
                except Exception:
                    parsed = None
            try:
                if isinstance(parsed, (dict, list)):
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                else:
                    pretty = str(raw)
            except Exception:
                pretty = str(raw)
            sms.api_response_pretty = pretty
