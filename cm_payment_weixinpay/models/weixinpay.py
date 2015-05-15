# -*- coding: utf-8 -*-

import logging

from openerp.osv import osv, fields
import time
import hashlib
import sys
import json
import urllib2
from openerp.tools.translate import _
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID
import datetime
import random
import werkzeug
import qrcode
from xml.dom import minidom as dom
import tempfile
import base64

reload(sys)
sys.setdefaultencoding('utf8')
_logger = logging.getLogger(__name__)


class AcquireWeixinpay(osv.Model):
    _inherit = 'payment.acquirer'
    _description = 'weixinpay'
    _columns = {
        'weixinpay_appid': fields.char(u'appid', help=u'必填,微信分配的公众账号ID'),
        'weixinpay_secret_key': fields.char(u'secret_key', help=u'必填,appid 密钥'),
        'weixinpay_payurl': fields.char(u'payurl', help=u'微信支付接口链接'),
        'weixinpay_mch_id': fields.char(u'mch_id', help=u'必填,微信支付分配的商户号'),
        'weixinpay_notify_url': fields.char(u'notify_url', help=u'必填,接收微信支付异步通知回调地址'),
    }

    _defaults = {
        'weixinpay_payurl': 'https://api.mch.weixin.qq.com/pay/unifiedorder',
        'weixinpay_notify_url': 'http://.../c/8/weixinpay/notify',
    }


    def _migrate_weixinpay_account(self, cr, uid, context=None):
        return True

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquireWeixinpay, self)._get_providers(cr, uid, context=context)
        providers.append(['weixinpay', 'Weixinpay'])
        return providers

    def _get_weixinpay_urls(self, cr, uid, environment, context=None):
        """ Weixinpay URLS """
        return {
            'weixinpay_url': 'https://mapi.weixinpay.com/gateway.do?',  # weixinpay接收数据url
        }

    def weixinpay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_weixinpay_urls(cr, uid, acquirer.environment, context=context)['weixinpay_url']

    # 跳转到本地订单页面

    # def weixinpay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
    # return 1

    def nonce_str(self):
        pstr = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        pwd = []
        for i in range(32):
            pwd.append(random.choice(pstr))
        nonce_str = ''.join(pwd)
        return nonce_str

    def createqrimage(self, cr, uid, ids, para, referenceid, context=None):
        # 创建二维码
        # 生成微信支付请求表单----------------------
        acquirer = self.browse(cr, uid, ids, context=context)
        sale_order = self.pool.get('sale.order')
        keylist = list(para.keys())
        keylist.sort()
        s = ''
        for i in range(len(keylist)):
            s += str(keylist[i]) + '=' + str(para[keylist[i]])
            if i != len(keylist) - 1:
                s += '&'

        s += '&key=' + acquirer['weixinpay_secret_key']
        signmd5 = hashlib.md5()
        signmd5.update(s)
        sign = (signmd5.hexdigest()).upper()
        # 生成微信支付请求++++++++++++++++++++++
        # 微信支付请求转换成xml----------------------------
        req = urllib2.Request(acquirer['weixinpay_payurl'])
        req.headers['Content-Type'] = 'text/xml'

        doc = dom.Document()
        root = doc.createElement('xml')
        doc.appendChild(root)

        for key, value in sorted(para.items()):
            newnode = doc.createElement(key)
            nodevalue = doc.createTextNode(str(value))
            newnode.appendChild(nodevalue)
            root.appendChild(newnode)
        signnode = doc.createElement('sign')
        signvalue = doc.createTextNode(sign)
        signnode.appendChild(signvalue)
        root.appendChild(signnode)
        req.data = doc.toprettyxml()
        # 微信支付请求转换成xml++++++++++++++++++++++++++++++++++
        # 获取微信支付url---------------------------
        response = urllib2.urlopen(req)
        resxml = dom.parse(response)
        return_code = resxml.getElementsByTagName('return_code')[0]
        flag = return_code.childNodes[0].nodeValue
        if flag == 'SUCCESS':
            code_urlnode = resxml.getElementsByTagName('code_url')
            if len(code_urlnode) != 0:
                code_url = code_urlnode[0].childNodes[0].nodeValue
                qrco = qrcode.QRCode()
                qrco.add_data(code_url)
                qrco.make()
                m = qrco.make_image()
                tmpf = tempfile.TemporaryFile()
                m.save(tmpf)
                tmpf.seek(0)
                sale_order.write(cr, uid, referenceid, {'weixinpay_qrcode': base64.b64encode(tmpf.read())})
                tmpf.close()
                logging.info(code_url)
                return True
            else:
                err_codenode = resxml.getElementsByTagName('err_code')[0]
                err_codevalue = err_codenode.childNodes[0].nodeValue
                err_code_des = resxml.getElementsByTagName('err_code_des')[0]
                err_code_des_value = err_code_des.childNodes[0].nodeValue
                logging.warning(u'没有获取到code_url:' + str(err_code_des_value))
                if err_codevalue == 'OUT_TRADE_NO_USED':
                    name = self.pool.get('ir.sequence').get(cr, 1, 'sale.order') or '/'
                    logging.warning(name+'======')
                    self.pool.get('sale.order').write(cr, 1, referenceid, {'name': name})
                    para['out_trade_no'] = name
                    logging.warning(self.pool.get('sale.order').browse(cr, 1, referenceid).name)
                    self.createqrimage(cr, uid, ids, para, referenceid, context=None)

                    return True
                return False
        else:
            result_msgnode = resxml.getElementsByTagName('return_msg')[0]
            result_msg = result_msgnode.childNodes[0].nodeValue
            logging.warning(u'请求支付url失败:' + str(result_msg))
            return False
            # 获取微信支付url+++++++++++++++++++++++++++++++++++

    def test(self, cr, uid, ids, context):
        '''
        测试参数是否配置正确,这里会跳转到支付页面
        '''

        acquirer = self.browse(cr, uid, ids, context=context)
        para = {}
        para['appid'] = acquirer['weixinpay_appid']
        para['mch_id'] = acquirer['weixinpay_mch_id']
        para['nonce_str'] = self.nonce_str()
        para['body'] = '测试商品'
        para['out_trade_no'] = self.nonce_str()[:10]
        para['total_fee'] = '1'
        para['trade_type'] = 'NATIVE'
        para['spbill_create_ip'] = '127.0.0.1'
        para['notify_url'] = 'http://www.100china.cn/weixinpay/notify'
        para['product_id'] = self.nonce_str()[:10]

        keylist = list(para.keys())
        keylist.sort()
        s = ''
        for i in range(len(keylist)):
            s += str(keylist[i]) + '=' + str(para[keylist[i]])
            if i != len(keylist) - 1:
                s += '&'

        s += '&key=' + acquirer['weixinpay_secret_key']
        signmd5 = hashlib.md5()
        signmd5.update(s)
        sign = (signmd5.hexdigest()).upper()
        # req = urllib2.Request(context['url'])
        req = urllib2.Request('https://api.mch.weixin.qq.com/pay/unifiedorder')
        req.headers['Content-Type'] = 'text/xml'

        doc = dom.Document()
        root = doc.createElement('xml')
        doc.appendChild(root)

        for key, value in sorted(para.items()):
            newnode = doc.createElement(key)
            nodevalue = doc.createTextNode(str(value))
            newnode.appendChild(nodevalue)
            root.appendChild(newnode)
        signnode = doc.createElement('sign')
        signvalue = doc.createTextNode(sign)
        signnode.appendChild(signvalue)
        root.appendChild(signnode)
        req.data = doc.toprettyxml()
        response = urllib2.urlopen(req)
        resxml = dom.parse(response)
        return_code = resxml.getElementsByTagName('return_code')[0]
        flag = return_code.childNodes[0].nodeValue
        if flag == 'SUCCESS':
            result_codenode = resxml.getElementsByTagName('result_code')[0]
            result_code = result_codenode.childNodes[0].nodeValue
            if result_code == 'SUCCESS':
                code_urlnode = resxml.getElementsByTagName('code_url')[0]
                code_url = code_urlnode.childNodes[0].nodeValue
                raise osv.except_osv(_('测试成功'), _('可以生成订单'))
            else:
                err_code_des = resxml.getElementsByTagName('err_code_des')[0]
                err_code_des_value = err_code_des.childNodes[0].nodeValue
                raise osv.except_osv(_('测试失败'), _(err_code_des_value))
        else:
            result_msgnode = resxml.getElementsByTagName('return_msg')[0]
            result_msg = result_msgnode.childNodes[0].nodeValue
            raise osv.except_osv(_('测试失败'), _(result_msg))
            # return True

    def weixinpay_form_generate_values(self, cr, uid, ids, partner_values, tx_values, context=None):
        '''
        生成支付支付参数
            '''
        acquirer = self.browse(cr, uid, ids, context=context)
        sale_order = self.pool.get('sale.order')
        referenceid = sale_order.search(cr, uid, [('name', '=', tx_values['reference'])])
        reference = sale_order.browse(cr, uid, referenceid)
        para = {}
        para['appid'] = acquirer['weixinpay_appid']
        para['mch_id'] = acquirer['weixinpay_mch_id']
        para['nonce_str'] = self.nonce_str()
        para['body'] = tx_values['reference']
        # para['out_trade_no'] = self.nonce_str()
        para['out_trade_no'] = tx_values['reference']
        para['total_fee'] = int(float(tx_values['amount']) * 100)
        para['trade_type'] = 'NATIVE'
        para['spbill_create_ip'] = '127.0.0.1'
        para['notify_url'] = acquirer['weixinpay_notify_url']
        para['product_id'] = tx_values['reference']
        tx_values['sale_order_id']=referenceid[0]
        print(referenceid)
        print('referenceid====================')
        if self.createqrimage(cr, uid, ids, para, referenceid, context):
            tx_values.update({'qrcode_url': '/c/8/weixinpay/qrcode?time=%s' % str(datetime.datetime.today())})
        else:
            tx_values.update({'qrcode_url': ''})
        return partner_values, tx_values


class TxWeixinPay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'refunds': fields.text(u'Reason for refund'),
        'date_order_refunds': fields.datetime(u'申请退款日期'),
        'date_confirm': fields.datetime(u'退款日期', copy=False),
        'user_id': fields.many2one('res.users', u'退款人'),
        'weixinpay_txn_id': fields.char('weixinpay Transaction ID'),
        'weixinpay_txn_type': fields.char('weixinpay Transaction type'),
        'payment_state': fields.selection(
            [('normal', u'正常'), ('refunds', u'申请退款'), ('pay_done', u'已支付'), ('pay_processing', u'等待支付'),
             ('refund_processing', u'等待退款'), ('refund_done', u'退款完成')], u'支付状态'),
    }

    def weixinpay_refund(self, cr, uid, ids, context):
        '''
        微信退款,系统没有设置退款功能,需要人工进入微商户系统进行退款
        '''
        if context is None:
            context = {}
        refund = self.browse(cr, 1, ids, context)
        if refund['payment_state'] == 'refund_done':
            raise osv.except_osv(_('重复退款'), _('退款已完成,请审核!'))
        elif refund['payment_state'] == 'pay_processing':
            raise osv.except_osv(_('退款失败'), _('支付未完成,请审核!'))
        else:
            raise osv.except_osv(_('退款失败'), _('系统暂不支持退款'))


    def refund(self, cr, uid, ids, context):
        rd = self.browse(cr, 1, ids, context)
        acquirer = (rd['acquirer_id']['name']).lower() + '_refund'
        if hasattr(self, acquirer):
            tx = getattr(self, acquirer)(cr, uid, ids, context=context)
        else:
            tx = ''
        return tx


class payment_sale_order(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'is_pay_success': fields.one2many('payment.transaction', 'sale_order_id', u'支付明细', readonly=True, copy=True),
        'weixinpay_qrcode': fields.binary(u'微信支付二维码', copy=True),
    }


