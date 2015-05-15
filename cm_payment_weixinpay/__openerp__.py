# -*- coding: utf-8 -*-

{
    'name': '微信支付',
    'summary': 'Payment weixinpay',
    'version': '1.0',
    'category': '',
    'sequence': 0,
    'author': 'canhuayin@gmail.com',
    'website': 'http://www.odoo.pw',
    'depends': ['base', 'payment', 'account', 'sale', 'portal', 'website_sale','cm_payment_alipay','payment_transfer'],
    'data': [
        'views/weixinpay_view.xml',
        'views/weixinpay.xml',
        'views/res_config_view.xml',
        'data/data.xml',


    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
    财付通
""",
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: