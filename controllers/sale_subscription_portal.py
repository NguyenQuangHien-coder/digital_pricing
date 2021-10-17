# -*- coding: utf-8 -*-
import json
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import NotFound
from werkzeug.urls import url_join
from odoo import http, tools, _
from odoo.http import request
import werkzeug


from odoo.addons.sale_subscription.controllers.portal import sale_subscription
from odoo.addons.portal.controllers.portal import get_records_pager

import logging
_logger = logging.getLogger(__name__)

class sale_subscription(http.Controller):

    @http.route(['/my/subscription/<int:account_id>/',
                 '/my/subscription/<int:account_id>/<string:uuid>'], type='http', auth="public", website=True)
    def subscription(self, account_id, uuid='', message='', message_class='', **kw):
        account_res = request.env['sale.subscription']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
            if request.uid == account.partner_id.user_id.id:
                account = account_res.browse(account_id)
        else:
            account = account_res.browse(account_id)

        acquirers = request.env['payment.acquirer'].search([
            ('state', 'in', ['enabled', 'test']),
            ('registration_view_template_id', '!=', False),
            ('token_implemented', '=', True),
            ('company_id', '=', account.company_id.id)])
        acc_pm = account.payment_token_id
        part_pms = request.env['payment.token'].search([
            ('acquirer_id.company_id', '=', account.company_id.id),
            ('partner_id', 'child_of', account.partner_id.commercial_partner_id.id)])
        display_close = account.template_id.sudo().user_closable and account.stage_category == 'progress'
        is_follower = request.env.user.partner_id.id in [follower.partner_id.id for follower in account.message_follower_ids]
        active_plan = account.template_id.sudo()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        if account.recurring_rule_type != 'weekly':
            rel_period = relativedelta(datetime.datetime.today(), account.recurring_next_date)
            missing_periods = getattr(rel_period, periods[account.recurring_rule_type]) + 1
        else:
            delta = datetime.date.today() - account.recurring_next_date
            missing_periods = delta.days / 7
        dummy, action = request.env['ir.model.data'].get_object_reference('sale_subscription', 'sale_subscription_action')

        # CUSTOM CODE     
        is_show_carousel = False
        is_stage_running = False
        is_first_invoice_server_paid = False
        package_sequence = -1
        key = account.license_key
        # days_left_of_server_package = 0
        # trial days
        server_payment_term_id = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        trial_days = request.env['account.payment.term'].sudo().browse(int(server_payment_term_id)).line_ids.days
        # get first invoice server
        first_invoice_server = request.env['account.move'].sudo().search(['&',('invoice_line_ids.subscription_id', '=', account.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1)
        
        for line in account.recurring_invoice_line_ids:
            if line.product_id.product_tmpl_id.is_value_package:
                is_show_carousel = True
                # package_sequence = line.product_id.sequence
                # current_product_id = line.product_id.id

        # cannot restart server when state = closed or renew
        for rec in account:
            if rec.stage_id.id != 3 and not rec.to_renew:
                is_stage_running = True

        if first_invoice_server.payment_state == 'paid':
            is_first_invoice_server_paid = True
            #GET DAYS LEFT OF CURRENT SERVER PACKAGE
            # days_left_of_server_package = int((account.recurring_next_date - date.today()).days)
            # if days_left_of_server_package < 0:
            #     days_left_of_server_package = 0
        # else:
           
        #     days_left_of_server_package = int((account.end_trial_date - date.today()).days)
        #     if days_left_of_server_package < 0:
        #         days_left_of_server_package = 0
        
        # get current server package
        current_server_package = request.env['sale.subscription.line'].sudo().search(['&',('analytic_account_id', '=', account.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
        product_tmpl_id = request.env['product.template'].sudo().search([('is_value_package', '=', True)], limit=1).id
        # products = request.env['product.product'].sudo().search(['&', ('product_tmpl_id', '=', product_tmpl_id), ('sequence', '>=', current_server_package.product_id.sequence)])
        products = request.env['product.product'].sudo().search(['&', ('product_tmpl_id', '=', product_tmpl_id), ('sale_price', '>=', current_server_package.product_id.lst_price)])
        digital_package_value = request.env['product.digitalpackage.value'].sudo().search([('is_server','=', True)])
        order = request.website.sale_get_order()
        
        if not products:
            is_show_carousel = False
        
        # RADIO SELECTION DATA
        digital_data = []
        for package in digital_package_value:
            digital_object = {}
            digital_object['package_id'] = package.id
            digital_object['package_name'] = package.name
            product_arr = []
            for product in products:
                if product.digital_package_value_id.id == package.id:     
                    o = {}
                    o['product_id'] = product.id
                    o['package_id'] = product.digital_package_value_id.id
                    product_arr.append(o)
            digital_object['products'] = product_arr
            digital_data.append(digital_object)

        # PRODUCT DATA
        products_data = []
        for product in products:
            # price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
            obj = {}
            if product.digital_package_value_id:
                for p in product.product_template_attribute_value_ids:
                    combination_info = product._get_combination_info_variant(pricelist=order.pricelist_id)   
                    obj['product_id'] = product.id
                    obj['package_id'] = product.digital_package_value_id.id
                    obj['uom_id'] = product.product_tmpl_id.uom_id.name
                    obj['package_seq'] = product.digital_package_value_id.sequence
                    obj[p.attribute_id.name] = p.name
                    # obj['price'] = p.product_tmpl_id.list_price + price_extra
                    obj['price'] = combination_info['price']
                products_data.append(obj)
        # END CUSTOM CODE
        values = {
            # CUSTOM CODE
            'package_sequence': package_sequence,
            'is_show_carousel': is_show_carousel,
            'digital_package_value': digital_package_value,
            'products': products_data,
            'data': digital_data,
            'trial_days': trial_days,
            'key': key,
            'is_stage_running': is_stage_running,
            # 'days_left_of_server_package': days_left_of_server_package,
            'account': account,
            # 'current_product_id': current_product_id,
            'current_server_package': current_server_package.product_id.id,
            'is_first_invoice_server_paid': is_first_invoice_server_paid,
            # END CUSTOM CODE
            'account': account,
            'template': account.template_id.sudo(),
            'display_close': display_close,
            'is_follower': is_follower,
            'close_reasons': request.env['sale.subscription.close.reason'].search([]),
            'missing_periods': missing_periods,
            'payment_mode': active_plan.payment_mode,
            'user': request.env.user,
            'acquirers': list(acquirers),
            'acc_pm': acc_pm,
            'part_pms': part_pms,
            'is_salesman': request.env['res.users'].with_user(request.uid).has_group('sales_team.group_sale_salesman'),
            'action': action,
            'message': message,
            'message_class': message_class,
            'change_pm': kw.get('change_pm') != None,
            'pricelist': account.pricelist_id.sudo(),
            'submit_class':'btn btn-primary mb8 mt8 float-right',
            'submit_txt':'Pay Subscription',
            'bootstrap_formatting':True,
            'return_url':'/my/subscription/' + str(account_id) + '/' + str(uuid),
        }

        history = request.session.get('my_subscriptions_history', [])
        values.update(get_records_pager(history, account))
        values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(account.recurring_total_incl, account.currency_id, account.partner_id.country_id)

        return request.render("sale_subscription.subscription", values)
        

    # UPGRADE PACKAGE
    @http.route(['/my/subscription/<int:account_id>/upgrade'], type='http', methods=["POST"], auth="public", website=True)
    def upgrade_account(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)
            #sale.subscription(7,)
        _logger.debug("===========account_id===========")
        _logger.debug("======================")
        _logger.debug("======================")
        _logger.debug("======================")
        _logger.debug(account)
       
        # get current subscription line
        # sub_line_id = request.env['sale.subscription.line'].sudo().search(['&',('analytic_account_id','=',account_id),('product_id.product_tmpl_id.is_value_package','=',True)],limit=1)
        if kw.get('package_id'):
            account.message_post(body=_('Upgrade package ID: %s', kw.get('package_id')))
            product_id = request.env['product.product'].sudo().browse(int(kw.get('package_id'))).id
            
            is_first_invoice_server_paid = False
            first_invoice_server = request.env['account.move'].sudo().search(['&',('invoice_line_ids.subscription_id', '=', account.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1)
            if first_invoice_server.payment_state == 'paid':
                is_first_invoice_server_paid = True
           
            current_sale_order = request.env['sale.order'].sudo().search(['&',('order_line.subscription_id', '=', account.id),('order_line.product_id','=',product_id)], order="id asc",limit=1)
        
            # REDIRECT TO OLD SALE ORDER (NOT PAID YET) WHEN CONFIRM UP SELL MODAL
            if is_first_invoice_server_paid and current_sale_order:
                return request.redirect(current_sale_order.get_portal_url())
            # CREATE NEW SALE ORDER WHEN CONFIRM UPSELL MODAL
            elif is_first_invoice_server_paid and not current_sale_order:
                # INHERIT FROM FUNCTION create_sale_order OF sale_subscription_wizard
                self = account.with_company(account.company_id)
                fpos = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
                sale_order_obj = self.env['sale.order']
                team = self.env['crm.team']._get_default_team_id(user_id=self.user_id.id)
                new_order_vals = {
                    'partner_id': self.partner_id.id,
                    'analytic_account_id': self.analytic_account_id.id,
                    'team_id': team and team.id,
                    'pricelist_id': self.pricelist_id.id,
                    'payment_term_id': self.payment_term_id.id,
                    'fiscal_position_id': fpos.id,
                    'subscription_management': 'upsell',
                    'origin': self.code,
                    'company_id': self.company_id.id,
                    'state': 'sent',       
                    # 'package_amount_left':old_package_amount_left + new_package_amount_left,
                    # 'payment_term_id': 1,
                }
                # we don't override the default if no payment terms has been set on the customer
                if self.partner_id.property_payment_term_id:
                    new_order_vals['payment_term_id'] = self.partner_id.property_payment_term_id.id
                order = sale_order_obj.create(new_order_vals)
                sale_order_obj.update
                order.message_post(body=(_("This upsell order has been created from the subscription ") + " <a href=# data-oe-model=sale.subscription data-oe-id=%d>%s</a>" % (self.id, self.display_name)))

                # INHERIT FROM FUNCTION partial_invoice_line OF sale_subscription
                order_line_obj = self.env['sale.order.line']
                ratio, message = account._partial_recurring_invoice_ratio(date_from=date.today())
                if message != "":
                    order.message_post(body=message)
                _discount = (1 - ratio) * 100
                values = {
                    'order_id': order.id,
                    'product_id': product_id,
                    'subscription_id': self.id,
                    #'product_uom_qty': option_line.quantity,
                    #'product_uom': option_line.uom_id.id,
                    'discount': _discount,
                    #'price_unit': self.pricelist_id.with_context(uom=option_line.uom_id.id).get_product_price(option_line.product_id, 1, False),
                    #'name': option_line.name,
                }
                order_line_obj.create(values)
                order.order_line._compute_tax_id()
                #CREATE SECTION DOWMPAYMENT WHEN UPSELL SERVER  
                #get current server package (last package)
                current_server_package = request.env['sale.subscription.line'].sudo().search(['&',('analytic_account_id', '=', self.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
                #check upsell server package
                is_server_package_upsell = request.env['sale.order.line'].sudo().search(['&',('order_id', '=', order.id),('product_id.product_tmpl_id.is_value_package','=',True)])
                #only create down payment when upselling server products and current subscription has server product too 
                if current_server_package and is_server_package_upsell:
                    # UPDATE payment_term_id WHEN UPSELL SERVER PACKAGE
                    order.update({
                    'payment_term_id': 1,
                    })
                    ratio, message = account._partial_recurring_invoice_ratio(date_from=date.today())
                    if message != "":
                        order.message_post(body=message)
                    _discount = (1 - ratio) * 100
                    section = {
                        'order_id': order.id,
                        'product_id': current_server_package.product_id.id,
                        'name': 'Down Payments',          
                        'display_type': 'line_section',
                        'is_server_upsell_downpayment': True
                    }
                    old_server = {
                        'order_id': order.id,
                        'product_id': current_server_package.product_id.id,
                        'subscription_id': self.id,         
                        'discount': _discount,
                        'is_downpayment': True,         
                        'product_uom_qty': -1 * current_server_package.quantity, 
                        'product_uom': current_server_package.uom_id.id,    
                    }
                    order_line_obj.create(section)
                    order_line_obj.create(old_server)
                    order.message_post(body=(_("A Down payment has been created from the Order ") + " <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>" % (order.id, order.name)))

                order_quotation = request.env['sale.order'].sudo().search([('order_line.subscription_id', '=', int(account_id))], order="id desc",limit=1)

                # AUTO SEND EMAIL
                template = request.env['mail.template'].sudo().browse(10)
                template.send_mail(order.id, force_send = True)
            
                return request.redirect(order_quotation.get_portal_url())
            else:
                return request.redirect(first_invoice_server.get_portal_url())

    # ACTIVATE PACKAGE
    @http.route(['/my/subscription/<int:account_id>/activate'], type='http', methods=["POST"], auth="public", website=True)
    def activate_package(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)
        
        first_invoice_server = request.env['account.move'].sudo().search(['&',('invoice_line_ids.subscription_id', '=', account.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1)
        return request.redirect(first_invoice_server.get_portal_url())

    # CHANGE DOMAIN
    @http.route(['/my/subscription/<int:account_id>/change-domain'], type='http', methods=["POST"], auth="public", website=True)
    def change_domain(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)

        if kw.get('domain') or kw.get('domain') == "":
            account.message_post(body=_('Upgrade domain: %s', kw.get('domain')))
            account.update({
                'domain': kw.get('domain')
            })       
        return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))
        
     # CHANGE ADDONS REPO
    @http.route(['/my/subscription/<int:account_id>/change-addons-repo'], type='http', methods=["POST"], auth="public", website=True)
    def change_addons_repo(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)


        if kw.get('addons_repo') or kw.get('addons_repo') == "":
            account.message_post(body=_('Upgrade domain: %s', kw.get('addons_repo')))
            account.update({
                'addons_repo': kw.get('addons_repo')
            })
        return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))

    # CHANGE DEPENDENCIES
    @http.route(['/my/subscription/<int:account_id>/change-dependencies'], type='http', methods=["POST"], auth="public", website=True)
    def change_dependencies(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)


        if kw.get('dependencies') or kw.get('dependencies') == "":
            account.message_post(body=_('Upgrade dependencies: %s', kw.get('dependencies')))
            account.update({
                'dependencies': kw.get('dependencies')
            })
        return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))