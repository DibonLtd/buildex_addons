# -*- coding: utf-8 -*-
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2024 DOTSPRIME SYSTEM LLP
#    Email : sales@dotsprime.com / dotsprime@gmail.com
########################################################

{
    'name': 'EAUT ZKTeco Integration',
    'version': '18.0.3.2.1',
    'category': 'Human Resources',
    'summary': 'Automate attendance by integrating ZKTeco biometric devices with Odoo.',
    'description': """
        DPS ZKTeco Biometric Attendance Integration
        ===========================================

        ZKTeco provides a Push SDK/API to facilitate integration—either by pushing attendance data to your system or periodically pulling it. This supports flexibility for building custom solutions (e.g., in Odoo or other frameworks)

        ZKTeco devices support ADMS (Automatic Device Management Service), enabling devices to push attendance data over HTTP/HTTPS, which is ideal for cloud platforms.

        Odoo ZKTeco Biometric Attendance Integration supports HTTP/ADMS, enabling webhook and cron-based syncing (every 10 mins) with cloud-hosted Odoo systems.

        ZKTeco Biometric Attendance Sync") fetches attendance logs from ZKTeco devices like F18 and K40, stores them in posgres database, and posts to your external API.

        This module seamlessly integrates "ZKTeco biometric devices" with "Odoo Attendance Management", providing real-time synchronization of attendance data for accurate HR processing.

        Key Features
        ------------
        ✅ ZKTeco devices with ADMS/WDMS/inbuilt web server capabilities can integrate
        ✅ Automatic synchronization of employee attendance from ZKTeco devices  
        ✅ Manage multiple biometric devices within Odoo  
        ✅ Sync employees across all devices with one click  
        ✅ Centralized view of attendance logs and device status  
        ✅ Configure attendance states for detailed reporting  
        ✅ Secure and reliable API communication with ZKTeco devices 
        ✅ Advance report option in PDf and Excel
        ✅ Calculate employee overe time
        ✅ Weekoff over time calculator 
        ✅ Calculate employee Breaktime
        ✅ Calculate employee shortfall

        Benefits
        --------
        ✅ Save HR time by eliminating manual attendance entry  
        ✅ Ensure accurate check-in/check-out tracking  
        ✅ Multi-company and multi-device compatible  

        Technical Details
        -----------------
        ✅ Compatible with Odoo 18 Community and Enterprise   
        ✅ Built for HR Attendance Management  
        ✅ Supports real-time data synchronization  
        """,
    'author': 'Dotsprime System',
    'sequence': 1,
    'price': 99,
    'currency': 'USD',
    "license": 'OPL-1', 
    'email': 'dotsprime@gmail.com',
    'support': 'sales@dotsprime.com',
    "website":'https://dotsprime.com/',
    'category': 'Human Resources',
    'license': 'AGPL-3',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/dashboard_dashboard.xml',
        'demo/dashboard_dashboard_demo.xml',
        'data/ir_cron.xml',
        'views/zkteco_device_settings_views.xml',
        'views/zkteco_device_logs.xml',
        'wizard/zkteco_device_attendance_create.xml',
        'wizard/zkteco_attendance_device_view.xml',
        'wizard/zkteco_device_attendance_report_view.xml',
        'wizard/employee_leave_assign_wizard.xml',
        'wizard/attendance_reports.xml',
        'views/views_inherit.xml',
        'views/attendance_state_views.xml',
        'views/zkteco_device_fingerprints.xml',
        'views/device_views.xml',
        'views/hr_attendance_view.xml',
        'views/hr_employee_view.xml',
        'views/resource_calendar_attendance_view.xml',
        'views/device_user_views.xml',

        'views/menus.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'dps_zkteco_biometric_integration/static/src/scss/zkteco_dashboard.scss'
        ]
    },
    "images": ['static/description/main_screenshot.png'],
    "live_test_url" : "",
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
