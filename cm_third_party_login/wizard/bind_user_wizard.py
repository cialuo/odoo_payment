# -*- coding: utf-8 -*-
##############################################################################
# OpenERP Connector
# Copyright 2013 Amos <sale@100china.cn>
##############################################################################

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.http import request
import werkzeug.utils


class payment_transaction_wizard(osv.osv_memory):
    _name = 'bind.user.wizard'
    _columns = {
        'login': fields.char(u'用户名', required=True, ),
        'password': fields.char(u'密码', required=True, ),
    }


    def but_yes(self, cr, uid, ids, context={}):
        obj = self.pool.get(context['active_model'])
        print(context)
        uid = context['uid']
        password = context['password']
        login = context['login']

        if not obj.browse(cr, 1, uid)['oauth_access_token']:
            raise osv.except_osv(_('绑定失败'), _('非外部用户登录!'))

        else:
            newuid = request.session.authenticate(request.session.db, login, password)
            if not newuid:
                request.session.authenticate(request.session.db, obj.browse(cr, 1, uid)['login'],
                                             obj.browse(cr, 1, uid)['oauth_access_token'])
                raise osv.except_osv(_('绑定失败'), _('请检查用户名和密码!'))
            else:
                oauths = self.pool.get('oauth.login.users')
                oauth = oauths.search(cr, 1, [('user_id', '=', uid), (
                    'oauth_access_token', '=', obj.browse(cr, 1, uid)['oauth_access_token'])])
                oauths.write(cr, 1, oauth, {'user_id': newuid})
                obj.write(cr, 1, newuid, {'oauth_access_token': obj.browse(cr, 1, uid)['oauth_access_token']})
                obj.write(cr, 1, uid, {'oauth_access_token': ''})
                cr.commit()
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/',
                    'nodestroy': True,
                    'target': 'self',
                }

    def but_no(self, cr, uid, ids, context={}):
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
