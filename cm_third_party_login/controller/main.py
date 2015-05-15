# -*- coding: utf-8 -*-
import functools
import logging
import urllib2
import urlparse
import simplejson
import urlparse
import time
import werkzeug.utils
from werkzeug.exceptions import BadRequest
import openerp
from werkzeug.wrappers import Response

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.addons.auth_oauth.controllers.main import OAuthLogin
from openerp.addons.web.controllers.main import db_monodb, ensure_db, set_cookie_and_redirect, login_and_redirect
from openerp.addons.auth_signup.controllers.main import AuthSignupHome as Home
from openerp.modules.registry import RegistryManager
from openerp.tools.translate import _
import random

_logger = logging.getLogger(__name__)


class thirdOAuthLogin(OAuthLogin):
    """继承
        website页面上面显示//淘宝登录//qq登录//链接
    """

    def list_providers(self):
        try:
            provider_obj = request.registry.get('auth.oauth.provider')
            providers = provider_obj.search_read(request.cr, SUPERUSER_ID,
                                                 [('enabled', '=', True), ('auth_endpoint', '!=', False),
                                                  ('validation_endpoint', '!=', False)])
            # TODO in forwardport: remove conditions on 'auth_endpoint' and 'validation_endpoint' when these fields will be 'required' in model
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                debug=request.debug,
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=simplejson.dumps(state),
            )
            if provider['name'] == 'taobao':
                params = {}
                params['client_id'] = provider['client_id']
                params['response_type'] = 'code'
                params['state'] = 'taobao'
                params['redirect_uri'] = provider['auth_oauth_taobao_redirect_uri']
            if provider['name'] == 'qq':
                params = {}
                params['client_id'] = provider['client_id']
                params['response_type'] = 'code'
                params['state'] = 'qq'
                params['redirect_uri'] = provider['auth_oauth_qq_redirect_uri']

            provider['auth_link'] = provider['auth_endpoint'] + '?' + werkzeug.url_encode(params)
        return providers


class thirdOAuthController(http.Controller):
    @http.route('/c/8/auth_oauth/signin2', type='http', auth='none')
    def signin2(self, **kw):
        """
        用于获取淘宝和qq的accesstoken获取之后在系统中注册新用户
        """
        try:
            pname = kw['state']
            u = request.registry.get('res.users')
            p = request.registry.get('auth.oauth.provider').search(request.cr, 1, [('name', 'ilike', pname)])[0]
            code = kw['code']
            provider = request.registry.get('auth.oauth.provider').browse(request.cr, 1, p)
            if pname == 'taobao':
                # 获取淘宝用户信息--------------
                params = {'client_id': provider['client_id'], 'client_secret': provider['auth_oauth_taobao_client_secret'],
                          'grant_type': 'authorization_code', 'code': code, 'state': 'token',
                          'redirect_uri': provider['auth_oauth_taobao_redirect_uri']}
                req = urllib2.Request('https://oauth.taobao.com/token')
                req.data = werkzeug.url_encode(params)
                f = urllib2.urlopen(req)
                response = f.read()
                post = simplejson.loads(response)

                access_token = post['access_token']
                taobao_user_nick = post['taobao_user_nick']
                taobao_user_id = post['taobao_user_id']
                # 获取淘宝用户信息++++++++++++++++

                ousers = request.registry.get('oauth.login.users')
                ouser = ousers.search(request.cr, 1, [('openid', '=', taobao_user_id)])

                if len(ouser) == 0:
                    # 注册并登录新用户
                    # 新用户随机密码---------------
                    pstr = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    pwd = []
                    for i in range(32):
                        pwd.append(random.choice(pstr))
                    pstr = ''.join(pwd)
                    # 新用户随机密码++++++++++++++
                    login = 'tb_' + time.strftime('%Y%m%d%H%M%S')
                    newuser = request.registry['res.users'].create(request.cr, 1,
                                                                   {'login': login,
                                                                    'name': taobao_user_nick,
                                                                    'password': pstr,
                                                                    'oauth_access_token': access_token})
                    request.cr.commit()  # as authenticate will use its own cursor we need to commit the current transaction
                    oid = ousers.create(request.cr, 1, {'oauth_access_token': access_token, "openid": taobao_user_id,
                                                        'provider_id': provider['id'], 'user_id': newuser,
                                                        })
                    return login_and_redirect(request.session.db, login, pstr, redirect_url='/shop')

                else:
                    # 跟新用户access_token
                    user = ousers.browse(request.cr, 1, ouser)['user_id']
                    u.write(request.cr, 1, user['id'],
                            {'oauth_access_token': access_token})
                    request.cr.commit()
                    ousers.write(request.cr, 1, ouser, {'oauth_access_token': access_token})
                    return login_and_redirect(request.session.db, user['login'], access_token, redirect_url='/shop')


            # qq登录
            elif pname == 'qq':
                params = {'client_id': provider['client_id'], 'client_secret': provider['auth_oauth_qq_client_secret'],
                          'grant_type': 'authorization_code', 'code': code, 'state': 'token',
                          'redirect_uri': provider['auth_oauth_qq_redirect_uri']}
                # 获取access token----
                getaccesstoken = urllib2.urlopen('https://graph.qq.com/oauth2.0/token' + '?', werkzeug.url_encode(params))
                post_accesstoken = urlparse.parse_qs(str(getaccesstoken.read()))
                # if {"error":100009,"error_description":"client secret is illegal"}
                if 'error' not in post_accesstoken.keys():
                    access_token = post_accesstoken['access_token'][0]
                else:
                    return post_accesstoken['error_description'] + '请联系管理员!'
                # 获取access token++++++

                # 获取openid----
                getopenid = urllib2.urlopen('https://graph.qq.com/oauth2.0/me' + '?',
                                            werkzeug.url_encode({'access_token': access_token}))
                openiddict = str(getopenid.read())[9:-3]
                openid = str(simplejson.loads(openiddict)['openid'])
                # 获取openid++++
                # 获取qq用户名----
                qqnamedict = urllib2.urlopen('https://graph.qq.com/user/get_user_info' + '?' + werkzeug.url_encode(
                    {'access_token': access_token, 'oauth_consumer_key': provider['client_id'], 'openid': openid}))
                qqname = str(simplejson.loads(qqnamedict.read())['nickname'])
                # 获取qq用户名++++


                ousers = request.registry.get('oauth.login.users')

                ouser = ousers.search(request.cr, 1, [('openid', '=', openid)])
                if len(ouser) == 0:
                    # 注册并登录新用户
                    # 新用户随机密码---------------
                    pstr = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    pwd = []
                    for i in range(32):
                        pwd.append(random.choice(pstr))
                    pstr = ''.join(pwd)
                    # 新用户随机密码++++++++++++
                    login = 'qq_' + time.strftime('%Y%m%d%H%M%S')
                    newuser = request.registry['res.users'].create(request.cr, 1,
                                                                   {'login': login,
                                                                    'name': qqname,
                                                                    'password': pstr,
                                                                    'oauth_access_token': access_token})
                    request.cr.commit()  # as authenticate will use its own cursor we need to commit the current transaction
                    oid = ousers.create(request.cr, 1, {'oauth_access_token': access_token, "openid": openid,
                                                        'provider_id': provider['id'], 'user_id': newuser,
                                                        })
                    return login_and_redirect(request.session.db, login, pstr, redirect_url='/shop')

                else:
                    # 更新access_token
                    user = ousers.browse(request.cr, 1, ouser)['user_id']
                    u.write(request.cr, 1, user['id'],
                            {'oauth_access_token': access_token})
                    request.cr.commit()
                    ousers.write(request.cr, 1, ouser, {'oauth_access_token': access_token})
                    return login_and_redirect(request.session.db, user['login'], access_token, redirect_url='/shop')
        except Exception:
            return '系统出现故障,请联系管理员!'

