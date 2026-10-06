import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry):
    """Post-init hook to ensure data consistency"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Get the existing SMS service
    IAPService = env['iap.service'].sudo()
    service = IAPService.search([('technical_name', '=', 'sms.sms')], limit=1)
    if not service:
        _logger.info("Creating SMS service with technical_name='sms.sms'")
        service = IAPService.create({
            'name': 'SMS Service',
            'technical_name': 'sms.sms',
            'description': 'Service for sending SMS',
            'unit_name': 'Credits'
        })
    
    # Get the XML-created account or create a new one
    IAPAccount = env['iap.account'].sudo()
    IrModel = env['ir.model.data'].sudo()
    
    try:
        default_account = IrModel.get_object('dibon_sms', 'iap_account_sms_dibon')
    except ValueError:
        default_account = IAPAccount.search([
            ('service_id.technical_name', '=', 'sms.sms'),
            ('sms_provider', '=', 'Dibon')
        ], limit=1)
    
    if not default_account:
        _logger.info("Creating new Dibon SMS account")
        default_account = IAPAccount.create({
            'name': 'Dibon SMS',
            'service_id': service.id,
            'sms_provider': 'Dibon',
            'state': 'enabled',
            'is_default_provider': True,
            'description': 'Default SMS provider configuration for Dibon'
        })
    
    # Always ensure the account is properly configured
    _logger.info("Updating Dibon SMS account configuration")
    default_account.write({
        'service_id': service.id,
        'sms_provider': 'Dibon',
        'state': 'enabled',
        'is_default_provider': True
    })
    
    # Consolidate any other Dibon accounts into the default_account
    duplicates = IAPAccount.search([('sms_provider', '=', 'Dibon'), ('id', '!=', default_account.id)])
    if duplicates:
        _logger.info('Merging %d duplicate Dibon accounts into %s', len(duplicates), default_account.name)
        for dup in duplicates:
            # Reassign SMS messages
            try:
                if dup.sms_ids:
                    dup.sms_ids.write({'provider_id': default_account.id})
            except Exception as e:
                _logger.exception('Failed to reassign sms_ids from %s: %s', dup.name, e)
            # Prefer to keep the description/credentials from default_account; otherwise we could merge fields here
            try:
                dup.unlink()
            except Exception as e:
                _logger.exception('Failed to unlink duplicate account %s: %s', dup.name, e)
