# -*- coding: utf-8 -*-

{
    'name': '支付宝支付',
    'summary': 'Payment Alipay',
    'version': '1.0',
    'category': '',
    'sequence': 0,
    'author': 'canhuayin@gmail.com',
    'website': 'http://www.odoo.pw',
    'depends': ['base', 'payment', 'account', 'sale', 'portal', 'website_sale','website','payment_transfer'],
    'data': [
        'security/sale_security.xml',
        'wizard/payment_transaction_wizard_view.xml',
        'views/payment_transaction_refunds_view.xml',
        'views/alipay_view.xml',
        'views/alipay.xml',
        'views/res_config_view.xml',
        'views/payment_sale_order_view.xml',
        'data/data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
支付宝
==================================
企业用户首先要申请支付宝接口,安装Alipay模块
菜单:设置//Payments//Payment Acquirers 配置支付宝帐号

功能
-------------
* 支付:用户付款成功后 执行回调 触发工作流
* 退款:用户申请退款,平台中心人员确认后触发原路退款,执行回调时修改退款成功状态

""",
}




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: