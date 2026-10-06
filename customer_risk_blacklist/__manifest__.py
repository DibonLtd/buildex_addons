{
    'name': 'Customer Risk Blacklist',
    'version': '18.0.1.0.0',
    'summary': 'Track bounced cheques and block blacklisted customers from credit sales',
    'category': 'Sales/Sales',
    'author': 'Dibon Consulting',
    'license': 'LGPL-3',
    'depends': ['contacts', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_bounced_cheque_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
