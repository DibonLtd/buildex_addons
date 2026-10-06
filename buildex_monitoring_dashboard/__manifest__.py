{
    'name': 'Buildex Monitoring Dashboard',
    'version': '18.0.1.0.0',
    'summary': 'Independent monitoring and data capture app for Buildex operations',
    'description': """
        Full phased implementation for the Buildex monitoring dashboard:
        - Customer master enrichment
        - Project tracking
        - Sale-to-project linkage
        - Fundi profiling
        - Post-purchase feedback capture
        - Follow-up operations
        - Monitoring queues and insights
        - Customer, fundi, and influencer scoring
    """,
    'category': 'Sales',
    'author': 'Custom',
    'depends': [
        'contacts',
        'mail',
        'sale_management',
        'account',
        'qr_referral_points',
        'website_sale_checkout_ke',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/buildex_sequence_data.xml',
        'data/buildex_taxonomy_data.xml',
        'views/buildex_fundi_request_views.xml',
        'views/buildex_followup_views.xml',
        'views/buildex_taxonomy_views.xml',
        'views/buildex_project_views.xml',
        'views/buildex_feedback_views.xml',
        'views/buildex_partner_views.xml',
        'views/buildex_sale_order_views.xml',
        'views/buildex_reporting_views.xml',
        'views/buildex_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'buildex_monitoring_dashboard/static/src/scss/buildex_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
