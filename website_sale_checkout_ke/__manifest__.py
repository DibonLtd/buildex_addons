{
    'name': 'Website Sale Checkout KE',
    'version': '18.0.1.0.0',
    'summary': 'Kenya-focused checkout rules for website sale',
    'category': 'Website',
    'author': 'Custom',
    'depends': ['website_sale', 'sales_team', 'sale_management', 'auth_signup'],
    'assets': {
        'web.assets_frontend': [
            'website_sale_checkout_ke/static/src/scss/checkout_ke.scss',
        ],
    },
    'data': [
        'data/res_partner_category_data.xml',
        'views/res_country_state_views.xml',
        'views/auth_signup_templates.xml',
        'views/crm_team_views.xml',
        'views/res_partner_views.xml',
        'views/fundi_menus.xml',
        'views/sale_order_views.xml',
        'views/sale_order_search_views.xml',
        'views/website_sale_templates.xml',
        'views/fundi_request_templates.xml',
    ],
    'installable': True,
    'application': False,
}
