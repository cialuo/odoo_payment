# -*- coding: utf-8 -*-

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _


class payment_transaction_wizard(osv.osv_memory):
    _name = 'payment.transaction.wizard'
    _columns = {
        'refunds': fields.text(u'Reason for refund',required=True,),
    }

    def _get_refunds(self, cr, uid, *args):
        return args[0]['refunds']


    def but_yes(self, cr, uid, ids, context={}):
        obj = self.pool.get(context['active_model'])
        parm = {
            'refunds': context['refunds'],
            'payment_state': 'refunds',
            'date_order_refunds': fields.date.context_today(self, cr, uid, context=context),
            'user_id': uid,
        }
        if  not obj.browse(cr,1, context['active_id'])['payment_state'] in ['normal','pay_done']:
            raise osv.except_osv(_('操作失败'),_('请检查当前订单的支付状态'))
        obj.write(cr, 1, context['active_id'], parm)
        return True

    def but_no(self, cr, uid, ids, context={}):
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
