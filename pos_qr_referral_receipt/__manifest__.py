{
    'name': 'POS QR Referral Receipt',
    'version': '18.0.1.0.0',
    'summary': 'Show the shop referral QR code from QR Referral Points on POS receipts',
    'category': 'Sales/Point of Sale',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'qr_referral_points'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_qr_referral_receipt/static/src/xml/order_receipt.xml',
        ],
    },
    'data': [],
    'installable': True,
    'application': False,
}
