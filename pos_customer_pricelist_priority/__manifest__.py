{
    'name': 'POS Customer Pricelist Priority',
    'version': '18.0.1.0.0',
    'summary': 'Use the selected customer pricelist first in POS, then fall back to the POS default pricelist',
    'category': 'Sales/Point of Sale',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_pricelist_priority/static/src/xml/control_buttons.xml',
            (
                'replace',
                'point_of_sale/static/src/app/generic_components/product_card/product_card.xml',
                'pos_customer_pricelist_priority/static/src/xml/product_card_compat.xml',
            ),
        ],
    },
    'data': [],
    'installable': True,
    'application': False,
}
