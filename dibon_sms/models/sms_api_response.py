from odoo import models, fields, api
import logging
import ast

_logger = logging.getLogger(__name__)


class SmsApiResponse(models.Model):
    _name = 'dibon.sms_api_response'
    _description = 'Dibon SMS API Responses'

    sms_id = fields.Many2one('sms.sms', string='SMS', ondelete='cascade', index=True)
    provider_id = fields.Many2one('iap.account', string='Provider', ondelete='set null')
    status = fields.Char(string='Gateway Status')
    status_code = fields.Char(string='Gateway Code')
    response_raw = fields.Text(string='Raw Response')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)

    @api.model
    def backfill_from_api_response_field(self, batch_size=200):
        """Backfill structured response records from existing `api_response` text on sms.sms records."""
        Sms = self.env['sms.sms'].sudo()
        domain = [('api_response', '!=', False), ('id', 'not in', self.search([]).mapped('sms_id').ids)]
        sms_records = Sms.search(domain, limit=batch_size)
        created = 0
        for sms in sms_records:
            try:
                # api_response was saved as str(dict) previously; try to parse safely
                data = sms.api_response
                parsed = None
                if not data:
                    continue
                try:
                    parsed = ast.literal_eval(data)
                except Exception:
                    # fallback to raw string
                    parsed = data
                vals = {
                    'sms_id': sms.id,
                    'provider_id': sms.provider_id.id if sms.provider_id else False,
                    'status': parsed.get('status') if isinstance(parsed, dict) else False,
                    'status_code': parsed.get('statusCode') if isinstance(parsed, dict) else False,
                    'response_raw': str(parsed)
                }
                self.create(vals)
                created += 1
            except Exception as e:
                _logger.exception('Failed to backfill sms %s: %s', sms.id, e)
        return created
