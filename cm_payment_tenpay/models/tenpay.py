# -*- coding: utf-8 -*-


import logging

from openerp.osv import osv, fields
import time
import hashlib
import sys
import bson
from openerp.tools.translate import _
import urllib
from xml.dom import minidom
import tempfile
import datetime
import requests
import httplib
import os

reload(sys)
sys.setdefaultencoding('utf8')


class Acquiretenpay(osv.Model):
    _inherit = 'payment.acquirer'
    _description = 'tenpay'
    _columns = {
        'tenpay_return_url': fields.char(u'支付同步通知URL', required=True),
        'tenpay_notify_url': fields.char(u'支付异步通知URL', required=True),
        'tenpay_refund_url': fields.char(u'退款通知URL', required=True),
        'tenpay_url': fields.char(u'财付通支付地址', required=True),
        'tenpay_refund_server_url': fields.char(u'财付通退款服务地址', help=u'', required=True),
        'tenpay_partner': fields.char(u'商户号', help=u'', required=True),
        'tenpay_key': fields.char(u'密钥', required=True),
        'tenpay_op_user_passwd': fields.char(u'财付通用户密码MD5值', required=True),
    }
    _defaults = {
        'tenpay_url': 'https://gw.tenpay.com/gateway/pay.htm',
        'tenpay_return_url': 'http://www.100china.cn/tenpay/return',
        'tenpay_notify_url': 'http://www.100china.cn/tenpay/notify',
        'tenpay_refund_url': 'http://www.100china.cn/tenpay/refund',
        'tenpay_refund_server_url': 'https://mch.tenpay.com/refundapi/gateway/refund.xml?',
        'tenpay_partner': '1212851101',
        'tenpay_key': 'ff27cdaf3bc3fca06072891a4fdbd23f',
        'tenpay_op_user_passwd': '96e79218965eb72c92a549dd5a330112'
    }


    def _migrate_tenpay_account(self, cr, uid, context=None):
        return True

    def _get_providers(self, cr, uid, context=None):
        providers = super(Acquiretenpay, self)._get_providers(cr, uid, context=context)
        providers.append(['tenpay', 'tenpay'])
        return providers

    def _get_tenpay_urls(self, cr, uid, environment, context=None):
        """ tenpay URLS """
        return {
            'tenpay_url': 'https://gw.tenpay.com/gateway/pay.htm',  # tenpay接收数据url
            'tenpay_return_url': 'http://localurl',  # 本地url服务器异步通知页面路径
            'tenpay_notify_url': 'http://localurl',  # 本地url页面跳转同步通知页面路径
        }

    def tenpay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_tenpay_urls(cr, uid, acquirer.environment, context=context)['tenpay_url']

    def tenpay_test(self, cr, uid, id, context):
        '''测死财付通配置是否正确'''
        tenpay_tx_values = {}
        acquirer = self.browse(cr, uid, id, context=context)
        tenpay_tx_values['return_url'] = acquirer['tenpay_return_url']
        tenpay_tx_values['notify_url'] = acquirer['tenpay_notify_url']
        tenpay_tx_values['partner'] = acquirer['tenpay_partner']

        tenpay_tx_values['total_fee'] = '1'
        tenpay_tx_values['body'] = 'test'
        tenpay_tx_values['fee_type'] = 1
        tenpay_tx_values['out_trade_no'] = 'test' + str(bson.ObjectId())
        tenpay_tx_values['charset'] = 'utf-8'
        tenpay_tx_values['type'] = 'MD5'
        tenpay_tx_values['spbill_create_ip'] = '121.1.4.11'

        keylist = [key for key in tenpay_tx_values.keys() if tenpay_tx_values[key] != '']
        keylist.sort()

        sign_str = ''
        for i in range(len(keylist)):
            sign_str += str(keylist[i]) + '=' + str(tenpay_tx_values[keylist[i]])
            if i != len(keylist) - 1:
                sign_str += '&'
        print(sign_str)
        sign = str(hashlib.md5(sign_str + '&key=' + acquirer['tenpay_key']).hexdigest()).upper()
        return {
            'type': 'ir.actions.act_url',
            'url': acquirer['tenpay_url'] + '?' + sign_str + '&sign=' + sign,
            'nodestroy': True,
            'target': 'new',
        }

    def tenpay_form_generate_values(self, cr, uid, ids, partner_values, tx_values, context=None):
        '''
        生成支付支付参数
        '''
        tenpay_tx_values = {}
        acquirer = self.browse(cr, uid, ids, context=context)
        tenpay_tx_values['return_url'] = acquirer['tenpay_return_url']
        tenpay_tx_values['notify_url'] = acquirer['tenpay_notify_url']
        tenpay_tx_values['partner'] = acquirer['tenpay_partner']

        tenpay_tx_values['total_fee'] = int(float(tx_values['amount']) * 100)  # 财付通以分为单位
        tenpay_tx_values['body'] = tx_values['reference']
        tenpay_tx_values['fee_type'] = 1
        tenpay_tx_values['out_trade_no'] = tx_values['reference']
        tenpay_tx_values['charset'] = 'utf-8'
        tenpay_tx_values['type'] = 'MD5'
        tenpay_tx_values['spbill_create_ip'] = '10.1.4.11'  # ip可以任意给
        # 生成签名------------
        keylist = [key for key in tenpay_tx_values.keys() if tenpay_tx_values[key] != '']
        keylist.sort()

        sign_str = ''
        for i in range(len(keylist)):
            sign_str += str(keylist[i]) + '=' + str(tenpay_tx_values[keylist[i]])
            if i != len(keylist) - 1:
                sign_str += '&'
        sign = str(hashlib.md5(sign_str + '&key=' + acquirer['tenpay_key']).hexdigest()).upper()
        # 生成签名++++++++++++++++++
        tx_values['sortkeylist'] = keylist
        tx_values['sign'] = sign
        tx_values['tenpay_form'] = tenpay_tx_values
        return partner_values, tx_values


class Txtenpay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'refunds': fields.text(u'Reason for refund'),
        'date_order_refunds': fields.datetime(u'申请退款日期'),
        'date_confirm': fields.datetime(u'退款日期', copy=False),
        'user_id': fields.many2one('res.users', u'退款人'),
        'tenpay_txn_id': fields.char('tenpay Transaction ID'),
        'tenpay_txn_type': fields.char('tenpay Transaction type'),
        'payment_state': fields.selection(
            [('normal', u'正常'), ('refunds', u'申请退款'), ('pay_done', u'已支付'), ('pay_processing', u'等待支付'),
             ('refund_processing', u'等待退款'), ('refund_done', u'退款完成')], u'支付状态'),
    }

    def tenpay_refund(self, cr, uid, ids, context):
        '''财付通退款'''
        # try:
        if context is None:
            context = {}
        refund = self.browse(cr, 1, ids, context)
        if refund['payment_state'] == 'refund_done':
            raise osv.except_osv(_('重复退款'), _('退款已完成,请审核!'))
        elif refund['payment_state'] == 'pay_processing':
            raise osv.except_osv(_('退款失败'), _('支付未完成,请审核!'))
        else:
            self.write(cr, 1, ids, {'payment_state': 'refund_processing', 'user_id': uid}, context)
        # 财付通退款参数------------
        value = {}
        refund = self.browse(cr, 1, ids, context=context)

        value['service_version'] = '1.1'
        value['partner'] = refund['acquirer_id']['tenpay_partner']
        value['transaction_id'] = refund['tenpay_txn_id']
        value['out_refund_no'] = time.strftime('%Y%m%d%H%M%S')
        value['total_fee'] = int(refund['amount'] * 100)  # 订单总金额
        value['refund_fee'] = int(refund['amount'] * 100)  # 退款金额
        value['op_user_id'] = refund['acquirer_id']['tenpay_partner']
        value['op_user_passwd'] = refund['acquirer_id']['tenpay_op_user_passwd']

        # MD5加密----------
        keylist = [key for key in value.keys() if value[key] != '']
        keylist.sort()

        sign_str = ''
        for i in range(len(keylist)):
            sign_str += str(keylist[i]) + '=' + str(value[keylist[i]])
            if i != len(keylist) - 1:
                sign_str += '&'
        sign = str(hashlib.md5(sign_str + '&key=' + refund['acquirer_id']['tenpay_key']).hexdigest()).upper()
        # MD5加密+++++++++
        #跳转到财付通退款页面
        return {
            'type': 'ir.actions.act_url',
            'url': refund['acquirer_id']['tenpay_refund_server_url'] + sign_str + '&sign=' + sign,
            'nodestroy': True,
            'target': 'new',
        }
        # except Exception:
        #     raise osv.except_osv(_('警告'), _('退款失败,请稍候再试!'))


    def tenpay_refund_state(self, cr, uid, ids, context):
        '''获取财付通退款状态'''
        try:
            refund = self.browse(cr, 1, ids, context=context)
            value = {}

            value['partner'] = refund['acquirer_id']['tenpay_partner']
            value['transaction_id'] = refund['tenpay_txn_id']
            value['input_charset'] = 'utf-8'

            keylist = [key for key in value.keys() if value[key] != '']
            keylist.sort()
            sign_str = ''
            for i in range(len(keylist)):
                sign_str += str(keylist[i]) + '=' + str(value[keylist[i]])
                if i != len(keylist) - 1:
                    sign_str += '&'
            sign = str(hashlib.md5(sign_str + '&key=' + refund['acquirer_id']['tenpay_key']).hexdigest()).upper()
            req = urllib.urlopen('https://gw.tenpay.com/gateway/normalrefundquery.xml?' + sign_str + '&sign=' + sign)
            res = req.read()
            dom = minidom.parseString(res).documentElement
            refund_state = dom.getElementsByTagName('refund_state_0')[0].firstChild.nodeValue
            if refund_state in ['4', '10']:
                refund.write({'payment_state': 'refund_done'})
            else:
                raise osv.except_osv(_('警告'), _('更新失败请稍后再试!'))
        except Exception:
            raise osv.except_osv(_('警告'), _('更新失败请稍后再试!'))







