{
    'name': 'ZI - Quant Excel Update',
    'version': '18.0',
    'summary': 'Update stock quant counted quantity via Excel',
    'author': 'ZI',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_quant_update_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
}
