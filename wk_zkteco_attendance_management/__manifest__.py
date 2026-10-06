# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################

{
    'name': 'ZKTeco Biometric Attendance Integration',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': """Odoo Zkteco Device Integration simplifies importing attendance data from the ZKTeco machine into Odoo.
    Biometric Attendance, webkul zkteco, biometric device integration, Smart Attendance Management, Auto Sync, Manual Sync, Sync Attendance, Auto Attendance Capture, Manual Attendance Sync, Smart Employee Enrollment, Employee Check-in Management, Employee Check-out Tracking, Break Time Logging, ADMS Mode, Cloud Based Attendance""",
    'author': 'Webkul Software Pvt. Ltd.',
    'license': 'Other proprietary',
    'website': 'https://store.webkul.com/odoo-zkteco-biometric-attendance-integration.html',
    'description': """ZKTeco Biometric Attendance Integration""",
    'live_test_url': 'http://odoodemo.webkul.com/?module=wk_zkteco_attendance_management',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/employee_enroll.xml',
        'views/attendance_machine_view.xml',
        'views/zkteco_feed.xml',
        'views/hr_attendance.xml',
    ],
    "images": ['static/description/Banner.png'],
    'external_dependencies': {
        'python': ['pyzk'],
        'bin': ['ping']
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 99,
    'currency': 'USD',
    'pre_init_hook': 'pre_init_check',
}
