from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class IapAccount(models.Model):
    _inherit = 'iap.account'
    
    sent_count = fields.Integer(string='Messages Sent', compute='_compute_sms_statistics')
    delivery_rate = fields.Float(string='Delivery Rate', compute='_compute_sms_statistics')
    
    @api.depends('sms_ids', 'sms_ids.state', 'sms_ids.delivery_status')
    def _compute_sms_statistics(self):
        for account in self:
            # Get messages for this provider
            messages = self.env['sms.sms'].sudo().search([('provider_id', '=', account.id)])
            
            # Calculate total sent
            total_sent = len(messages)
            account.sent_count = total_sent
            
            # Calculate delivery rate
            if total_sent > 0:
                successful = len(messages.filtered(lambda m: m.state == 'sent' or m.delivery_status == 'delivered'))
                account.delivery_rate = (successful / total_sent) * 100
            else:
                account.delivery_rate = 0.0
    
    def action_send_sms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send SMS',
            'res_model': 'sms.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                # Preselect the current user's partner so the composer opens with a recipient
                'default_partner_ids': [(6, 0, [self.env.user.partner_id.id])],
                'default_numbers': '',
            },
            'view_id': self.env.ref('sms.sms_composer_view_form').id,
            # Do not force a custom view id here; use the default composer view so buttons behave correctly
        }
    
    def action_view_settings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SMS Settings',
            'res_model': 'iap.account',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'view_id': self.env.ref('dibon_sms.iap_account_view_form').id,
            'context': {
                'create': False,
                'form_view_ref': 'dibon_sms.iap_account_view_form',
                'default_service_id': self.service_id.id,
                'default_sms_provider': self.sms_provider
            },
            'flags': {'form': {'action_buttons': True}}
        }
