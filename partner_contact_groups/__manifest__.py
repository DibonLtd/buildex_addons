{
    'name': 'Partner Contact Groups',
    'version': '18.0.1.0.0',
    'summary': 'Tag contacts and customers by business role',
    'category': 'Contacts',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/partner_contact_group_data.xml',
        'views/partner_contact_group_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
