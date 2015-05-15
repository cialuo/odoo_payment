# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

import logging

_logger = logging.getLogger(__name__)


class oauth_login_users(osv.Model):
    _name = 'oauth.login.users'
    _columns = {
        'user_id': fields.many2one('res.users', u'系统用户'),
        'oauth_access_token': fields.char(u'access_token'),
        'openid': fields.char(u'oauth_uid/openid'),
        'provider_id': fields.many2one('auth.oauth.provider', u'外部用户'),
    }