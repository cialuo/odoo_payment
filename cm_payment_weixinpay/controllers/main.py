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
import os
from jinja2 import FileSystemLoader, Environment
from xml.dom import minidom as dom
from xml.etree import ElementTree as et
import tempfile
import httplib

_logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
templateLoader = FileSystemLoader(searchpath=BASE_DIR + "/templates")
env = Environment(loader=templateLoader)


class weixinpayController(http.Controller):
    @http.route('/c/8/weixinpay/qrcode')
    def weixinpay_qrcode(self, **post):
        '''返回微信支付二维码'''
        print(post)
        # sale_orders = request.registry.get('sale.order').search(request.cr, 1,
        #                                                         [('name', '=', post.get('reference', ''))])
        sale_order = request.registry.get('sale.order').browse(request.cr, 1, [int(post['sale_order_id'])])
        print(sale_order)
        print(int(post['sale_order_id']))
        template = env.get_template("qrcode.html")
        html = template.render({'sale_order': sale_order,
                                'redirect_url': '/web?#action=mail.action_mail_redirect&model=sale.order&res_id=%s' %
                                                int(post['sale_order_id'])})
        return html

    @http.route('/c/8/weixinpay/checkstate')
    def weixinpay_checkstate(self, **post):
        '''用户浏览器轮寻订单支付结果,用于跳转'''
        tx_id = request.registry['payment.transaction'].search(request.cr, 1,
                                                               [('reference', '=', post.get('name', ''))])
        if tx_id:
            tx = request.registry['payment.transaction'].browse(request.cr, 1, tx_id)
            if tx['payment_state'] == 'pay_done':
                return 'True'
            else:
                return 'False'

        else:
            return 'False'


    @http.route('/c/8/weixinpay/notify', type='http', auth="none")
    def weixinpay_return(self, **post):
        # 微信支付结果回调
        # 微信支付结果以xml形式返回
        # 解析xml-----------------
        data = request.httprequest.data
        tmp = tempfile.TemporaryFile()
        tmp.write(data)
        tmp.seek(0)
        returndoc = et.parse(tmp)
        nodes = returndoc.getiterator()
        return_values = {}
        for node in nodes:
            if node.tag != 'xml' and node.tag != 'sign':
                return_values[node.tag] = node.text
        tmp.close()
        # 解析xml++++++++++++++++
        acquirerid=request.registry.get('payment.acquirer').search(request.cr,1,[('name','=','weixin')])
        acquirer=request.registry.get('payment.acquirer').browse(request.cr,1,acquirerid)
        keylist = list(return_values.keys())
        keylist.sort()
        s = ''
        for i in range(len(keylist)):
            s += str(keylist[i]) + '=' + str(return_values[keylist[i]])
            if i != len(keylist) - 1:
                s += '&'
        s += '&key=' + acquirer['weixinpay_secret_key']
        signmd5 = hashlib.md5()
        signmd5.update(s)
        checksign = (signmd5.hexdigest()).upper()

        if return_values.get('return_code', '') == 'SUCCESS':
            out_trade_no = return_values['out_trade_no']
            saleid = request.registry['sale.order'].search(request.cr, 1, [('name', '=', out_trade_no)])
            print(saleid)
            sale = request.registry['sale.order'].browse(request.cr, 1, saleid)
            partner = request.registry['res.partner'].browse(request.cr, 1, sale['partner_id']['id'])
            # 生成支付结果---------------
            if checksign==return_values.get('sign',''):
                tx_values = {}
                tx_values['acquirer_id'] = \
                    request.registry['payment.acquirer'].search(request.cr, 1, [('name', '=', 'weixinpay')])[0]
                tx_values['type'] = 'form'
                tx_values['reference'] = out_trade_no
                tx_values['amount'] = float(return_values['total_fee']) / 100
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
                tx_values['weixinpay_txn_type'] = 'qrcode'
                tx_values['weixinpay_txn_id'] = return_values['transaction_id']

                request.registry['sale.order'].signal_workflow(request.cr, SUPERUSER_ID, saleid, 'order_confirm')
                request.registry['sale.order'].write(request.cr, 1, saleid, {'state': 'manual'})
                request.session['sale_order_id'] = None
                if float(sale['amount_total']) != float(return_values['total_fee']) / 100:

                    tx_values['state_message'] = u'支付异常,支付金额有误!'
                else:
                    tx_values['state_message'] = u'支付成功'
                tx_values['state'] = 'done'
                tx_values['payment_state'] = 'pay_done'
                # 生成支付结果++++++++++++++++++
                # 更新或创建支付结果------------
                tx_id = request.registry['payment.transaction'].search(request.cr, 1,
                                                                       [('reference', '=', out_trade_no)],
                                                                       context=None)

                if tx_id:
                    update = request.registry['payment.transaction'].write(request.cr, 1, tx_id, tx_values,
                                                                           context=None)
                else:
                    tx_id = request.registry['payment.transaction'].create(request.cr, 1, tx_values, context=None)
                    # 更新或创建支付结果++++++++++++++++
                response = '''<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'''
                return response
            else:
                return ''
            # else:
            # return ''

        else:
            return ''
