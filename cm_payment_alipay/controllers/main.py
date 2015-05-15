# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import urllib2
import hashlib
import werkzeug.utils
from openerp import http, SUPERUSER_ID
from openerp.http import request
import datetime

_logger = logging.getLogger(__name__)


class alipayController(http.Controller):
    @http.route('/c/8/alipay/return', type='http', auth="none")
    def alipay_return(self, **post):
        # 支付宝支付结果回调
        try:
            cr, uid, context = request.cr, request.uid, request.context
            is_success = post.get('is_success', 'F')
            sign = post.get('sign', '')
            name = post.get('subject', '')
            notify_id = post.get('notify_id', '')

            # 验证是否是支付宝的请求 checksign==sign and flag==TRUE# -----------
            req = urllib2.urlopen(
                'https://mapi.alipay.com/gateway.do?service=notify_verify&partner=%s&notify_id=%s' % (
                    post.get('seller_id', ''), notify_id))
            flag = str(req.read()).upper()
            responsedict = {}
            for key in post.keys():
                if key != 'sign' and key != 'sign_type':
                    responsedict[key] = post[key]
            keylist = responsedict.keys()
            keylist.sort()
            s = ''
            for i in range(len(keylist)):
                s += str(keylist[i]) + '=' + str(responsedict[keylist[i]])
                if i != len(keylist) - 1:
                    s += '&'

            acquirer = request.registry['payment.acquirer'].search_read(cr, 1, [('name', '=', 'alipay')])
            checksign = str(hashlib.md5(s + acquirer[0]['alipay_key']).hexdigest())
            #验证是否是支付宝的请求  checksign==sign and flag==TRUE++++++++++

            #订单信息---------
            saleid = request.registry['sale.order'].search(cr, 1, [('name', '=', name)])
            sale = request.registry['sale.order'].browse(cr, 1, saleid)
            partner = request.registry['res.partner'].browse(cr, 1, sale['partner_id']['id'])
            tx_values = {}
            tx_values['acquirer_id'] = request.registry['payment.acquirer'].search(cr, 1, [('name', '=', 'alipay')])[0]
            tx_values['type'] = 'form'
            tx_values['reference'] = name
            tx_values['amount'] = float(post['total_fee'])
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
            tx_values['alipay_txn_type'] = 'create_direct_pay_by_user'
            tx_values['alipay_txn_id'] = post['trade_no']
            if sign == checksign and flag == 'TRUE' and is_success == 'T':
                request.registry['sale.order'].signal_workflow(cr, SUPERUSER_ID, saleid, 'order_confirm')
                request.registry['sale.order'].write(cr, 1, saleid, {'state': 'manual'})
                request.session['sale_order_id'] = None
                if float(sale['amount_total']) != float(post['total_fee']):

                    tx_values['state_message'] = u'支付异常,支付金额有误!'
                else:
                    tx_values['state_message'] = u'支付成功'
                tx_values['state'] = 'done'
                tx_values['payment_state'] = 'pay_done'
            else:
                tx_values['state_message'] = u'等待交易中'
                tx_values['state'] = 'draft'
                tx_values['payment_state'] = 'pay_processing'
            #订单信息+++++++++++

            #修改或者添加payment transaction然后跳转到订单详情页面
            tx_id = request.registry['payment.transaction'].search(cr, uid, [('reference', '=', name)],
                                                                   context=context)

            if tx_id:
                update = request.registry['payment.transaction'].write(cr, 1, tx_id, tx_values,
                                                                       context=context)
            else:
                tx_id = request.registry['payment.transaction'].create(cr, 1, tx_values, context=context)
            return werkzeug.utils.redirect(
                '/web?#action=mail.action_mail_redirect&model=sale.order&res_id=%s' % saleid[0])
        except Exception:
            werkzeug.utils.redirect('/')


    @http.route('/c/8/alipay/refund', type='http', auth="none")
    def refund(self, **post):
        # 支付宝退款回调
        try:
            acquirer = request.registry['payment.acquirer'].search_read(request.cr, 1, [('name', '=', 'alipay')])

            # 验证是否是支付宝的请求  checksign==sign and flag==TRUE------------
            req = urllib2.urlopen(
                'https://mapi.alipay.com/gateway.do?service=notify_verify&partner=%s&notify_id=%s' % (
                    acquirer[0]['alipay_partner'], post['notify_id']))
            flag = str(req.read()).upper()
            responsedict = {}
            for key in post.keys():
                if key != 'sign' and key != 'sign_type':
                    responsedict[key] = post[key]
            keylist = responsedict.keys()
            keylist.sort()
            s = ''
            for i in range(len(keylist)):
                s += str(keylist[i]) + '=' + str(responsedict[keylist[i]])
                if i != len(keylist) - 1:
                    s += '&'
            checksign = str(hashlib.md5(s + acquirer[0]['alipay_key']).hexdigest())
            sign = post['sign']
            #验证是否是支付宝的请求  checksign==sign and flag==TRUE++++++++++


            #支付宝发来的订单的退款信息---------
            result_details = post['result_details']
            trade_no = result_details.split('^')[0]  #订单号
            state = result_details.split('^')[2].upper()  #退款状态
            #支付宝发来的订单的退款信息++++++++


            if flag == 'TRUE' and state == 'SUCCESS' and sign == checksign:
                refundid = request.registry.get('payment.transaction').search(request.cr, 1,
                                                                              [('alipay_txn_id', '=', str(trade_no))])

                parm = {

                    'payment_state': 'refund_done',
                    'date_confirm': datetime.datetime.now(),
                }

                request.registry.get('payment.transaction').write(request.cr, 1, refundid, parm)
                return 'success'
            else:
                return ''
        except Exception:
            return ''


