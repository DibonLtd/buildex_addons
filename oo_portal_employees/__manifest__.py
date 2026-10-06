# -*- coding: utf-8 -*-
{
    'name': 'Portal Employees',
    'version': '18.0.0.1.0',
    'author': 'Eric Macharia',
    'website': 'http://teclea.co.ke',
    'summary': 'Employee self service on portal.',
    'description': """
        View and download paylips
        View and apply for leaves
        Employee Managers can view and approve their employees leaves.
    """,
    'depends': ['portal', 'mail', 'hr_payroll', 'hr_holidays', 'hr_appraisal', 'survey'],
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'data/email_templates.xml',
        
        'views/leaves_template.xml',
        'views/payslip_template.xml',
        'views/appraisal_template.xml'
    ]
}
