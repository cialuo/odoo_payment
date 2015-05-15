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


reload(sys)
sys.setdefaultencoding('utf8')
_logger = logging.getLogger(__name__)


class AcquireAlipay(osv.Model):

    _inherit = 'payment.acquirer'
    _description = 'alipay'
    _columns = {
        'alipay_service': fields.char(u'接口名称', help=u'接口名称,create_direct_pay_by_user'),
        'alipay_partner': fields.char(u'合作者身份ID', help=u'签约的支付宝账号对应的支付宝唯一用户号,以 2088 开头的 16 位纯数字组成'),
        'alipay_input_charset': fields.char(u'参数编码字符集', help=u'商户网站使用的编码格式,如utf-8、gbk、gb2312 等'),
        'alipay_sign_type': fields.char(u'签名方式', help=u'DSA、RSA、MD5 三个值可选,必须大写,这里请默认填写utf-8'),
        'alipay_seller_email': fields.char(u'用户名', help=u'卖家支付宝帐户'),
        'alipay_out_trade_no': fields.char(u'商品唯一订单号', help=u'商户网站订单系统中唯一订单号，必填'),
        'alipay_key': fields.char(u'安全检验码', help=u'以数字和字母组成的32位字符'),

        'alipay_subject': fields.char(u'商品名', help=u'商品的名称'),
        'alipay_payment_type': fields.char(u'支付类型', size=128, help=u'商品的标题/交易标题/订单标题/订单关键字等。'),
        'alipay_total_fee': fields.char(u'交易金额',
                                        help=u'该笔订单的资金总额,单位为RMB-Yuan。取值范围为[0.01,100000000.00],精确到小数点后两位。'),
        'alipay_url': fields.char(u'alipay网址'),
        'alipay_return_url': fields.char(u'alipay支付结果通知页面', help=u'本地地址'),
        'alipay_refund_notify_url': fields.char(u'支付宝退款通知页面', help=u'本地地址处理退款'),
    }

    _defaults = {
        'alipay_seller_email': 'sale@100china.cn',
        'alipay_key': 'mx8omr8yo1ln01tm0w7aiqvwodmuh0uu',
        'alipay_partner': '2088111179700649',
        'alipay_service': 'create_direct_pay_by_user',
        'alipay_input_charset': 'utf-8',
        'alipay_sign_type': 'MD5',
        'alipay_payment_type': '1',
        'alipay_url': 'https://mapi.alipay.com/gateway.do?',
        'alipay_return_url': 'http://121.40.86.103:8069/c/8/alipay/return',
        'alipay_refund_notify_url': 'http://121.40.86.103:8069/c/8/alipay/refund'


    }


    def _migrate_alipay_account(self, cr, uid, context=None):
        return True

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquireAlipay, self)._get_providers(cr, uid, context=context)
        providers.append(['alipay', 'Alipay'])
        return providers

    def _get_alipay_urls(self, cr, uid, environment, context=None):
        """ Alipay URLS """
        return {
            'alipay_url': 'https://mapi.alipay.com/gateway.do?',  # alipay接收数据url
        }

    def alipay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_alipay_urls(cr, uid, acquirer.environment, context=context)['alipay_url']

    # def alipay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
    # return 1

    def test(self, cr, uid, id, context):
        '''
        测试参数是否配置正确,这里会跳转到支付页面
        '''
        acquirer = self.browse(cr, uid, id, context=context)
        para = {}
        para['service'] = acquirer['alipay_service']
        para['partner'] = acquirer['alipay_partner']
        para['seller_email'] = acquirer['alipay_seller_email']
        para['_input_charset'] = acquirer['alipay_input_charset']
        para['payment_type'] = acquirer['alipay_payment_type']
        para['out_trade_no'] = time.time()
        para['total_fee'] = '0.1'
        para['subject'] = '测试商品'
        para['return_url'] = context['return_url']
        keylist = list(para.keys())
        keylist.sort()
        print(keylist)
        s = ''
        for i in range(len(keylist)):
            s += str(keylist[i]) + '=' + str(para[keylist[i]])
            if i != len(keylist) - 1:
                s += '&'
        sign = str(hashlib.md5(s + context['key']).hexdigest())
        s += '&sign=' + sign + '&sign_type=MD5'
        s = context['url'] + s
        print(s)
        return {
            'type': 'ir.actions.act_url',
            'url': s,
            'nodestroy': True,
            'target': 'new',
        }

    def alipay_form_generate_values(self, cr, uid, ids, partner_values, tx_values, context=None):
        '''
        生成支付支付参数
        '''
        acquirer = self.browse(cr, uid, ids, context=context)
        tx_values['_input_charset'] = acquirer['alipay_input_charset']
        tx_values['out_trade_no'] = tx_values['reference'] + str(time.time())
        tx_values['partner'] = acquirer['alipay_partner']
        tx_values['payment_type'] = acquirer['alipay_payment_type']
        tx_values['seller_email'] = acquirer['alipay_seller_email']
        tx_values['total_fee'] = tx_values['amount']
        tx_values['subject'] = tx_values['reference']
        tx_values['sign_type'] = acquirer['alipay_sign_type']
        tx_values['service'] = acquirer['alipay_service']
        tx_values['return_url'] = acquirer['alipay_return_url']
        # 生成签名----------------
        para = {}
        para['service'] = acquirer['alipay_service']
        para['partner'] = acquirer['alipay_partner']
        para['seller_email'] = acquirer['alipay_seller_email']
        para['_input_charset'] = acquirer['alipay_input_charset']
        para['payment_type'] = acquirer['alipay_payment_type']
        para['out_trade_no'] = tx_values['out_trade_no']
        para['total_fee'] = tx_values['total_fee']
        para['subject'] = tx_values['subject']
        para['return_url'] = tx_values['return_url']

        keylist = list(para.keys())
        keylist.sort()
        s = ''
        for i in range(len(keylist)):
            s += str(keylist[i]) + '=' + str(para[keylist[i]])
            if i != len(keylist) - 1:
                s += '&'
        sign = str(hashlib.md5(s + acquirer['alipay_key']).hexdigest())
        # 生成签名+++++++++++++++++++
        tx_values['sign'] = sign
        tx_values['sortkeylist'] = keylist
        return partner_values, tx_values


class TxAliPay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'refunds': fields.text(u'Reason for refund'),
        'date_order_refunds': fields.datetime(u'申请退款日期'),
        'date_confirm': fields.datetime(u'退款日期', copy=False),
        'user_id': fields.many2one('res.users', u'退款人'),
        'alipay_txn_id': fields.char('alipay Transaction ID'),
        'alipay_txn_type': fields.char('alipay Transaction type'),
        'payment_state': fields.selection(
            [('normal', u'正常'), ('refunds', u'申请退款'), ('pay_done', u'已支付'), ('pay_processing', u'等待支付'),
             ('refund_processing', u'等待退款'), ('refund_done', u'退款完成')], u'支付状态'),
    }

    def alipay_refund(self, cr, uid, ids, context):
        '''
        支付宝退款
        '''
        try:
            if context is None:
                context = {}
            refund = self.browse(cr, 1, ids, context)
            if refund['payment_state'] == 'refund_done':
                raise osv.except_osv(_('重复退款'), _('退款已完成,请审核!'))
            elif refund['payment_state'] == 'pay_processing':
                raise osv.except_osv(_('退款失败'), _('支付未完成,请审核!'))
            else:
                self.write(cr, 1, ids, {'payment_state': 'refund_processing', 'user_id': uid}, context)

            #支付宝退款参数
            value = {}
            refund = self.browse(cr, 1, ids, context=context)
            value['_input_charset'] = refund['acquirer_id']['alipay_input_charset']
            value['notify_url'] = refund['acquirer_id']['alipay_refund_notify_url']
            value['service'] = 'refund_fastpay_by_platform_pwd'
            value['partner'] = refund['acquirer_id']['alipay_partner']
            value['seller_email'] = refund['acquirer_id']['alipay_seller_email']
            value['seller_user_id'] = refund['acquirer_id']['alipay_partner']
            value['refund_date'] = time.strftime('%Y-%m-%d %H:%M:%S')#固定格式
            value['batch_num'] = 1#一次退款一个订单
            value['batch_no'] = time.strftime('%Y%m%d') + '00' + str(refund['id'])#按照固定格式
            trade_no = str(refund['alipay_txn_id'])
            amont_total = str(refund['amount'])
            value['detail_data'] = u'%s^%s^%s' % (trade_no, amont_total, refund['refunds'])

            #对参数进行MD5加密获得sign
            keylist = list(value.keys())
            keylist.sort()
            s = ''
            for i in range(len(keylist)):
                s += str(keylist[i]) + '=' + str(value[keylist[i]])
                if i != len(keylist) - 1:
                    s += '&'
            sign = str(hashlib.md5(s + refund['acquirer_id']['alipay_key']).hexdigest())

            s += '&sign=' + sign + '&sign_type=MD5'
            #跳转至支付宝退款页面
            return {
                'type': 'ir.actions.act_url',
                'url': refund['acquirer_id']['alipay_url'] + s,
                'nodestroy': True,
                'target': 'new',
            }
        except Exception:
            raise osv.except_osv(_('警告'), _('退款失败,请稍候再试!'))

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
    }

