{
    "name": "Dibon SMS",
    "summary": "Send SMS to custom endpoint",
    "version": "18.0.1.0.0",
    "author": "Dibon Consulting LTd",
    "website": "https://www.dibon.co.ke/",
    "category": "Extra Tools",
    "depends": ["sms", "web"],
    "license": "OPL-1",
    "data": [
        "data/iap_services.xml",
        "views/iap_actions.xml",
        "views/iap_views.xml",
        "views/dashboard_views.xml",
    "views/menu_items.xml",
    "views/sms_composer_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dibon_sms/static/src/css/dashboard.css",
        ],
    },
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["Dibon Consulting"],
    "hooks": {
        "post_init": "post_init_hook"
    },
    "auto_install": False,
}
