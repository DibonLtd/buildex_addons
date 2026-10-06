# -*- coding: utf-8 -*-
#############################################################################
#

#
#############################################################################
{
    'name': 'SignUp With Dibon SMS',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Mobile number signup with OTP verification via Dibon SMS.',
    'description': """Module helps users sign up using their mobile number
    and verify it with a one-time password (OTP) via Dibon SMS. Additionally,
    the option to sign up with an email ID is also available.""",
    'author': 'Gibeongideon',
    'company': 'Dibon Consulting',
    'maintainer': 'Gibeongideon',
    'website': '',
    'depends': ['portal', 'auth_signup', 'mail','dibon_sms'],
    'data': [
        'views/res_config_setting_views.xml',
        'views/signup_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'signup_with_dibon_sms/static/src/css/signup.css',
            'signup_with_dibon_sms/static/**/*',
        ],
    },
    # 'external_dependencies': {
    #     'python': ['twilio']
    # },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
