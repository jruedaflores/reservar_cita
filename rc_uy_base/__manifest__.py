# -*- coding: utf-8 -*-
{
    'name': "RC UY Base",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,
    'sequence': 150,
    'author': "RUDA",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': '',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['rc_uy_update', 'mail'],

    # always loaded
    'data': [
        'security/rc_base_security.xml',
        'security/ir.model.access.csv',
        'wizard/rc_generate_schedule_views.xml',
        'data/rc_params_config_data.xml',
        'views/rc_params_config_views.xml',
        'views/rc_resource_views.xml',
        'views/rc_human_resource_views.xml',
        'views/rc_consumer_views.xml',
        'views/rc_consumer_test_drive_views.xml',
        'views/rc_booking_views.xml',
        'views/rc_schedule_views.xml',
        'views/menuitem_views.xml',
    ],
}
