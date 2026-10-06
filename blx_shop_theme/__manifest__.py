{
    'name': 'Dibon Shop Theme',
    'version': '18.0.2.0.0',
    'summary': 'Modern cosmetic overhaul for the Dibon e-commerce shop',
    'category': 'Website/Website',
    'author': 'Gibeongideon',
    'depends': ['website_sale'],
    'data': [
        'views/shop_override.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'blx_shop_theme/static/src/css/shop.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
