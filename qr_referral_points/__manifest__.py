
{
    'name': 'QR Referral & Points',
    'version': '18.0.1.0.0',
    'summary': 'QR-based referral system for Odoo 18 eCommerce with points',
    'category': 'Website',
    'author': 'Dibon Consulting,gibeongideon',
    'depends': ['base', 'portal', 'website','sale', 'website_sale', 'sale_management', 'account'],

    'assets': {
        'web.assets_frontend': [
            'qr_referral_points/static/src/css/influencer_portal.css',
            'qr_referral_points/static/src/js/influencer_portal.js',
        ],
    },

    'data': [
        'security/ir.model.access.csv',

        'data/sequence.xml',
        'views/influencer_sales_main_menu.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/influencer_wallet_views.xml',
        'views/influencer_commission_rule_views.xml',
        'views/influencer_commission_batch_views.xml',
        'views/product_template_views.xml',

        'views/website_menus.xml',
        'views/influencer_partner_menus.xml',
        'views/influencer_link_performance_views.xml',
        'views/influencer_sales_order_menus.xml',
        'views/influencer_commission_menu.xml',
        'views/influencer_commission_plan_menu.xml',
        'views/influencer_program_config_views.xml',

        'templates/influencer_landing.xml',
        'templates/influencer_application.xml',
        'templates/influencer_portal.xml',
        'templates/mobile_signup.xml',
        ],




    'installable': True,
    'application': False,
}

#  test
