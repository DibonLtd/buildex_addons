{
    'name': 'POS Payment Reference Popup',
    'version': '18.0.1.0.0',
    'summary': 'Prompt for a payment reference when selecting POS payment methods',
    'category': 'Sales/Point of Sale',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_reference_popup/static/src/js/pos_payment.js',
            'pos_payment_reference_popup/static/src/js/payment_screen.js',
            'pos_payment_reference_popup/static/src/xml/payment_lines.xml',
            'pos_payment_reference_popup/static/src/xml/order_receipt.xml',
        ],
    },
    'data': [
        'views/pos_payment_method_views.xml',
        'views/pos_payment_views.xml',
    ],
    'installable': True,
    'application': False,
}
