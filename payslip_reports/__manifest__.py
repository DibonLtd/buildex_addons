# -*- coding: utf-8 -*-
{
    'name': "Payslip Reports",
    'description': "Payslip Reports",
    'author': 'Awais',
    'website': "http://www.xyz.com",
    'category': 'HR',
    'version': '18.0.1.1',
    'application': True,
    'depends': ['base', 'web', 'hr','hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'report/report.xml',
        'report/module_report.xml',
        'report/payroll_report_summary.xml',
        'wizard/payslip_view.xml',
        'wizard/payroll.xml',
        'data/mail.xml',
             ],

    'installable': True,
    'auto_install': False,
}
