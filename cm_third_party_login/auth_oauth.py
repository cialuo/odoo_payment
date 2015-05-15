# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

import logging

_logger = logging.getLogger(__name__)


class base_config_settings(osv.Model):
    _inherit = 'auth.oauth.provider'
    _columns = {
        'auth_oauth_taobao_redirect_uri': fields.char('redirect_uri', help=u'重定向地址,需要进行UrlEncode'),
        'auth_oauth_taobao_client_secret': fields.char('client_secret', help=u'appsecret'),

        'auth_oauth_qq_redirect_uri': fields.char('redirect_uri', help=u'qq验证返回地址', ),
        'auth_oauth_qq_client_secret': fields.char('client_secret', help=u'申请QQ登录成功后，分配给网站的appkey', ),
    }

