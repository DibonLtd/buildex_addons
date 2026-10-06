{
    'name': 'Influencer Program',
    'version': '18.0.1.0.0',
    'summary': 'Standalone influencer management dashboard',
    'description': """
        Complete backend for managing the influencer programme:
        - Applications & approvals with kanban pipeline
        - Performance: commissions, wallet, referral visits
        - Referred sales pipeline
        - Topline network & recruitment
        - Configuration: commission plans, programme terms
    """,
    'category': 'Marketing',
    'author': 'Dibon Consulting',
    'depends': ['qr_referral_points', 'sale_management'],
    'data': [
        'security/influencer_groups.xml',
        'security/ir.model.access.csv',
        'views/ip_influencer_views.xml',
        'views/ip_performance_views.xml',
        'views/ip_sales_views.xml',
        'views/ip_network_views.xml',
        'views/ip_config_views.xml',
        'views/ip_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}
