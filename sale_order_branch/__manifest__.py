{
    'name': 'Sale Order Branch',
    'version': '18.0.1.0.0',
    'summary': 'Add branch selection on sales orders',
    'category': 'Sales',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['contacts', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_branch_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
