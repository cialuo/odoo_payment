# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class ResCompany(osv.Model):
    _inherit = "res.company"

    def _get_weixinpay_account(self, cr, uid, ids, name, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        weixinpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('name', 'ilike', 'weixinpay'),
            ('company_id', '=', company_id),
        ], limit=1, context=context)
        if weixinpay_ids:
            weixinpay = Acquirer.browse(cr, uid, weixinpay_ids[0], context=context)
            return dict.fromkeys(ids, weixinpay.weixinpay_email_account)
        return dict.fromkeys(ids, False)

    def _set_weixinpay_account(self, cr, uid, id, name, value, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        weixinpay_account = self.browse(cr, uid, id, context=context).weixinpay_account
        weixinpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('weixinpay_email_account', '=', weixinpay_account),
            ('company_id', '=', company_id),
        ], context=context)
        if weixinpay_ids:
            Acquirer.write(cr, uid, weixinpay_ids, {'weixinpay_email_account': value}, context=context)
        return True

    _columns = {
        'weixinpay_account': fields.function(
            _get_weixinpay_account,
            fnct_inv=_set_weixinpay_account,
            nodrop=True,
            type='char', string='weixinpay Account',
            help="weixinpay username (usually email) for receiving online payments."
        ),
    }
