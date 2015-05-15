# -*- coding: utf-8 -*-
##############################################################################
# OpenERP Connector
# Copyright 2013 Amos <sale@100china.cn>
################################################a##############################


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



{
    'name': '第三方登录',
    'summary': 'QQ,taobao登录接口',
    'version': '1.0',
    'category': '',
    'sequence': 0,
    'author': 'canhuayin@gmail.com',
    'website': 'http://www.odoo.pw',
    'depends': ['base', 'base_setup', 'auth_oauth', 'website','web'],
    'data': [
        'wizard/bind_user_wizard_view.xml',
        'data/third_party_login.xml',
        'res_config.xml',
        'view/mainlayout.xml',
        'view/login_icon.xml',
        'user_bind_view.xml',
        'user_form_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
    qq 淘宝登录
""",
}
