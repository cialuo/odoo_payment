# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib2
import werkzeug
import hashlib
from openerp import http, SUPERUSER_ID
from openerp.http import request
import datetime

_logger = logging.getLogger(__name__)


class tenpayController(http.Controller):
    @http.route('/c/8/tenpay/return', type='http', auth="none")
    def tenpay_return(self, **post):
        '''财付通支付结果回调'''
        cr, uid, context = request.cr, request.session.uid, request.context
        name = post['out_trade_no']
        # 验证是否是是否是腾讯发来的请求 sign==checksign-------------
        sign = post['sign']
        keylist = [key for key in post.keys() if key != 'sign']
        keylist.sort()
        sign_str = ''
        for i in range(len(keylist)):
            sign_str += str(keylist[i]) + '=' + str(post[keylist[i]])
            if i != len(keylist) - 1:
                sign_str += '&'

        saleid = request.registry['sale.order'].search(cr, 1, [('name', '=', name)])
        sale = request.registry['sale.order'].browse(cr, 1, saleid)
        acquirer = request.registry['payment.acquirer'].search_read(cr, 1, [('name', '=', 'tenpay')])

        checksign = str(hashlib.md5(sign_str + '&key=' + acquirer[0]['tenpay_key']).hexdigest()).upper()
        # 验证是否是是否是腾讯发来的请求 sign==checksign-------------

        #订单信息------
        partner = request.registry['res.partner'].browse(cr, 1, sale['partner_id']['id'])
        tx_values = {}
        tx_values['acquirer_id'] = request.registry['payment.acquirer'].search(cr, 1, [('name', '=', 'tenpay')])[0]
        tx_values['type'] = 'form'
        tx_values['reference'] = name
        tx_values['amount'] = float(post['total_fee']) / 100

        tx_values['currency_id'] = sale['currency_id']['id']
        tx_values['partner_id'] = sale['partner_id']['id']
        tx_values['partner_name'] = partner['name']
        tx_values['partner_lang'] = partner['lang']
        tx_values['partner_email'] = partner['email']
        tx_values['partner_zip'] = partner['zip']
        tx_values['partner_address'] = partner['street']
        tx_values['partner_city'] = partner['city']
        tx_values['partner_country_id'] = partner['country_id']['id'] or 49
        tx_values['partner_phone'] = partner['phone']
        tx_values['partner_reference'] = partner['name']

        tx_values['tenpay_txn_type'] = u'快捷支付'
        tx_values['tenpay_txn_id'] = post['transaction_id']
        #订单信息++++++++++

        #根据请求支付状态修改订单信息,然后跳转到订单详情----------
        if sign == checksign:
            request.registry['sale.order'].signal_workflow(cr, SUPERUSER_ID, saleid, 'order_confirm')
            request.registry['sale.order'].write(cr, 1, saleid, {'state': 'manual'})
            request.session['sale_order_id'] = None
            if float(sale['amount_total']) != float(post['total_fee']) / 100:

                tx_values['state_message'] = u'支付异常,支付金额有误!'
            else:
                tx_values['state_message'] = u'支付成功'
            tx_values['state'] = 'done'
            tx_values['payment_state'] = 'pay_done'

        else:
            tx_values['state_message'] = u'等待交易中'
            tx_values['state'] = 'draft'
            tx_values['payment_state'] = 'pay_processing'
        tx_id = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', name)],
                                                               context=context)

        if tx_id:
            update = request.registry['payment.transaction'].write(cr, 1, tx_id, tx_values, context=context)
        else:
            tx_id = request.registry['payment.transaction'].create(cr, 1, tx_values, context=context)
        return werkzeug.utils.redirect('/web?#action=mail.action_mail_redirect&model=sale.order&res_id=%s' % saleid[0])
        #根据请求支付状态修改订单信息,然后跳转到订单详情+++++++++++

    @http.route('/c/8/tenpay/notify', type='http', auth="none")
    def tenpay_notify(self, **post):
        cr, uid, context = request.cr, request.session.uid, request.context
        name = post['out_trade_no']

        sign = post['sign']
        keylist = [key for key in post.keys() if key != 'sign']
        keylist.sort()
        sign_str = ''
        for i in range(len(keylist)):
            sign_str += str(keylist[i]) + '=' + str(post[keylist[i]])
            if i != len(keylist) - 1:
                sign_str += '&'

        saleid = request.registry['sale.order'].search(cr, 1, [('name', '=', name)])
        sale = request.registry['sale.order'].browse(cr, 1, saleid)
        acquirer = request.registry['payment.acquirer'].search_read(cr, 1, [('name', '=', 'tenpay')])

        checksign = str(hashlib.md5(sign_str + '&key=' + acquirer[0]['tenpay_key']).hexdigest()).upper()

        partner = request.registry['res.partner'].browse(cr, 1, sale['partner_id']['id'])
        tx_values = {}
        tx_values['acquirer_id'] = request.registry['payment.acquirer'].search(cr, 1, [('name', '=', 'tenpay')])[0]
        tx_values['type'] = 'form'
        tx_values['reference'] = name
        tx_values['amount'] = float(post['total_fee']) / 100

        tx_values['currency_id'] = sale['currency_id']['id']
        tx_values['partner_id'] = sale['partner_id']['id']
        tx_values['partner_name'] = partner['name']
        tx_values['partner_lang'] = partner['lang']
        tx_values['partner_email'] = partner['email']
        tx_values['partner_zip'] = partner['zip']
        tx_values['partner_address'] = partner['street']
        tx_values['partner_city'] = partner['city']
        tx_values['partner_country_id'] = partner['country_id']['id'] or 49
        tx_values['partner_phone'] = partner['phone']
        tx_values['partner_reference'] = partner['name']

        tx_values['tenpay_txn_type'] = u'快捷支付'
        tx_values['tenpay_txn_id'] = post['transaction_id']

        if sign == checksign:

            request.registry['sale.order'].signal_workflow(cr, SUPERUSER_ID, saleid, 'order_confirm')
            request.registry['sale.order'].write(cr, 1, saleid, {'state': 'manual'})
            request.session['sale_order_id'] = None

            if float(sale['amount_total']) != float(post['total_fee']) / 100:

                tx_values['state_message'] = u'支付异常,支付金额有误!'
            else:
                tx_values['state_message'] = u'支付成功'
            tx_values['state'] = 'done'
            tx_values['payment_state'] = 'pay_done'
        else:
            tx_values['state_message'] = u'等待交易中'
            tx_values['state'] = 'draft'
            tx_values['payment_state'] = 'pay_processing'
        tx_id = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', name)],
                                                               context=context)
        if tx_id:
            update = request.registry['payment.transaction'].write(cr, 1, tx_id, tx_values, context=context)
        else:
            tx_id = request.registry['payment.transaction'].create(cr, 1, tx_values, context=context)
        return 'success'

