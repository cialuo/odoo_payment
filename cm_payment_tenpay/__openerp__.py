# -*- coding: utf-8 -*-

{
    'name': ' 财付通支付',
    'summary': 'Payment tenpay',
    'version': '1.0',
    'category': '',
    'sequence': 0,
    'author': 'canhuayin@gmail.com',
    'website': 'http://www.odoo.pw',
    'depends': ['base', 'payment', 'account','sale','portal','website_sale','cm_payment_alipay','payment_transfer'],
    'data': [
        'views/tenpay_view.xml',
        'views/tenpay.xml',
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