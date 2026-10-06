# -*- coding: utf-8 -*-
#############################################################################
#

#
#############################################################################
{
    'name': 'SignUp With Mobile',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'A Module For SignUp With Mobile Number.',
    'description': """Module helps users sign up using their mobile number
    and verify it with a one-time password (OTP) by Twilio. Additionally, the
     option to sign up with an email ID is also available""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['portal', 'auth_signup', 'mail','dibon_sms'],
    'data': [
        'views/res_config_setting_views.xml',
        'views/signup_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'signup_with_twilio/static/src/css/signup.css',
            'signup_with_twilio/static/**/*',
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
