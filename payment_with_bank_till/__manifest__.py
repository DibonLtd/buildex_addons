{
    'name': 'Payment Provider: Bank Paybill (Equity)',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 360,
    'summary': 'Pay via Equity Bank Paybill. Customer sends payment and submits reference.',
    'description': ' ',
    'depends': ['payment', 'website_sale'],
    'data': [
        'views/payment_bank_till_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_with_bank_till/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
