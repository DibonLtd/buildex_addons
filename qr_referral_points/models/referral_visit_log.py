import urllib.request
import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = ('127.', '10.', '192.168.', '::1', 'localhost')


def _lookup_location(ip):
    """Call ip-api.com to get country/region/city for an IP.
    Returns a dict with visitor_country, visitor_region, visitor_city.
    Returns empty dict on failure or private IP.
    """
    if not ip or any(ip.startswith(p) for p in _PRIVATE_PREFIXES):
        return {}
    try:
        url = f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city'
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get('status') == 'success':
                return {
                    'visitor_country': data.get('country', ''),
                    'visitor_region': data.get('regionName', ''),
                    'visitor_city': data.get('city', ''),
                }
    except Exception as e:
        _logger.warning("IP geolocation failed for %s: %s", ip, e)
    return {}


class InfluencerReferralVisitLog(models.Model):
    _name = 'influencer.referral.visit.log'
    _description = 'Influencer Referral Visit Log'
    _order = 'visit_datetime desc'

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        index=True,
        ondelete='cascade',
        string='Influencer',
    )
    visit_datetime = fields.Datetime(
        string='Visited At',
        default=fields.Datetime.now,
        required=True,
    )
    visitor_ip = fields.Char(string='Visitor IP')
    visitor_country = fields.Char(string='Country')
    visitor_region = fields.Char(string='Region / State')
    visitor_city = fields.Char(string='City')
    gps_lat = fields.Float(string='GPS Latitude', digits=(10, 7))
    gps_lng = fields.Float(string='GPS Longitude', digits=(10, 7))
    gps_accuracy = fields.Float(string='GPS Accuracy (m)')

    @classmethod
    def _get_visitor_ip(cls, request):
        """Extract real visitor IP, respecting X-Forwarded-For."""
        forwarded = request.httprequest.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.httprequest.remote_addr or ''
