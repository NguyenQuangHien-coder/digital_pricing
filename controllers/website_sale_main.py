
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import datetime
from datetime import date, datetime
from dateutil.relativedelta import TU, relativedelta
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import ValidationError
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

class WebsiteSale(http.Controller):

    # BUY NOW BUTTON
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        
        """This route is called when adding a product to cart (no options)."""
        sale_order = request.website.sale_get_order(force_create=True)
        # CUSTOM CODE
        # order = request.website.sale_get_order()
        # if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
	    #     return request.redirect('/web/login?redirect=/shop/checkout')

        # check selected is server product ?
        is_server_product = request.env['product.product'].sudo().browse(int(product_id)).product_tmpl_id.is_value_package
        # unlink old server product before include new sever product
        for line in sale_order.order_line:
            if line.product_id.product_tmpl_id.is_value_package and is_server_product:          
                line.unlink()           
        # END-CUSTOM CODE
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        product_custom_attribute_values = None
        if kw.get('product_custom_attribute_values'):
            product_custom_attribute_values = json.loads(kw.get('product_custom_attribute_values'))

        no_variant_attribute_values = None
        if kw.get('no_variant_attribute_values'):
            no_variant_attribute_values = json.loads(kw.get('no_variant_attribute_values'))
        # update cart
        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values
        )

        if kw.get('express'):
            return request.redirect("/shop/checkout?express=1")

        return request.redirect("/shop/cart")

    # 30 DAYS FREE TRIAL BUTTON
    @http.route(['/shop/cart/try-demo'], type='http', auth="public", methods=['GET'], website=True)
    def try_demo(self, **kw):
       

        #self = account.with_company(account.company_id)
        #fpos = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        res = request.env['sale.order'].create({
            'partner_id': 7,
            'require_payment': True,
        })

        request.env['sale.order.line'].create({
            'product_id': 1,
            'order_id': res.id,
        })
    
    # INHERIT
    # RETURN /MY/SUBSCRIPTION AFTER PAYMENT IF HAVE SERVER PRODUCT IN ORDER LINE 
    # @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    # def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
    #     if sale_order_id is None:
    #         order = request.website.sale_get_order()
    #     else:
    #         order = request.env['sale.order'].sudo().browse(sale_order_id)
    #         assert order.id == request.session.get('sale_last_order_id')
    #     # CUSTOM CODE
    #     account_id = order.order_line.subscription_id.recurring_invoice_line_ids.analytic_account_id.id
    #     uuid = order.order_line.subscription_id.uuid
    #     for line in order.order_line:
    #         if line.product_id.product_tmpl_id.is_value_package:
    #             return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))
    #     # END CUSTOM CODE
    #     return request.redirect('/shop/confirmation')
    

    # INHERIT
    # RETURN /MY/SUBSCRIPTION AFTER PAYMENT IF HAVE SERVER PRODUCT IN ORDER LINE 
    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)
            assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx:
            order.with_context(send_email=True).action_confirm()
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')
       
        PaymentProcessing.remove_payment_transaction(tx)
        
        # CUSTOM CODE
        # account_id = order.order_line.subscription_id.recurring_invoice_line_ids.analytic_account_id.id
        # uuid = order.order_line.subscription_id.uuid
        # for line in order.order_line:
        #     if line.product_id.product_tmpl_id.is_value_package:
        #         return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))
        # END CUSTOM CODE
        return request.redirect('/shop/confirmation') 

    def order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order for Google analytics basically defined to be inherited """
        return {
            'transaction': {
                'id': order.id,
                'affiliation': order.company_id.name,
                'revenue': order.amount_total,
                'tax': order.amount_tax,
                'currency': order.currency_id.name
            },
            'lines': self.order_lines_2_google_api(order.order_line)
        }
    
    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            # account_id = order.order_line.subscription_id.recurring_invoice_line_ids.analytic_account_id.id
            account_id = order.order_line.subscription_id.id
            uuid = order.order_line.subscription_id.uuid
            # for line in order.order_line:
            #     if order.state == 'sale' and line.product_id.product_tmpl_id.is_value_package:
            #         return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))
            #     else:
            #         return request.render("website_sale.confirmation", {'order': order})
            is_server_package = False
            if order.state == 'sale':
                for line in order.order_line:
                    if line.product_id.product_tmpl_id.is_value_package:
                        is_server_package = True
            if is_server_package:
                # order.update({
                #     'payment_term_id':2,
                # })
                return request.redirect('/my/subscription/%s/%s' % (account_id, uuid))
            else:    
                return request.render("website_sale.confirmation", {'order': order})

        else:
            return request.redirect('/shop')
    
    # SET PRICE 
    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token(self, pm_id=None, **kwargs):
        """ Method that handles payment using saved tokens

        :param int pm_id: id of the payment.token that we want to use to pay.
        """
        order = request.website.sale_get_order()
        # do not crash if the user has already paid and try to pay again
        if not order:
            return request.redirect('/shop/?error=no_order')

        assert order.partner_id.id != request.website.partner_id.id

        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/shop/?error=invalid_token_id')
        # CUSTOM CODE
        
        if kwargs.get('is_trial') == "trialpayment":
            first_invoice_percent = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.first_invoice_percent')
            for orders in order:
               # SET PRICE DEFAULT
                amount_trial_package = tax_trial_packagge = 0.0
                default_server_price = trial_30days_server_price = default_server_tax = trial_30days_server_tax = 0.0
                default_model_price = trial_30days_model_price = default_model_tax = trial_30days_model_tax = 0.0
                # GET PRICE OF SERVER PRODUCT IN sale_order_line
                for line in orders.order_line:
                    # order_line = request.env['sale.order.line'].sudo().search([('id','=',line.id),('product_id.product_tmpl_id.is_value_package','=',True)])
                    #default price
                    if line.product_id.product_tmpl_id.is_value_package:
                        default_server_price += line.price_subtotal
                        #trial price
                        trial_30days_server_price += int(line.price_subtotal/100*int(first_invoice_percent))
                        #default tax
                        default_server_tax += line.price_tax
                        #trial tax
                        trial_30days_server_tax += int(line.price_tax/100*int(first_invoice_percent))

                    # GET PRICE OF MODEL PRODUCT IN sale_order_line
                    if line.product_id.product_tmpl_id.categ_id.is_digital_category:
                        default_model_price += line.price_subtotal
                        #trial price
                        trial_30days_model_price += int(line.price_subtotal/100*int(first_invoice_percent))
                        #default tax
                        default_model_tax += line.price_tax
                        #trial tax
                        trial_30days_model_tax += int(line.price_tax/100*int(first_invoice_percent))
                # GET PRICE AND TAX OF FULLPAYMENT
                orders.amount_untaxed = orders.amount_tax = 0.0
                for line in orders.order_line:                 
                    orders.amount_untaxed += line.price_subtotal
                    orders.amount_tax += line.price_tax
                    
                # GET PRICE AND TAX OF TRIAL 30DAYS
                amount_trial_package += int(orders.amount_untaxed - default_server_price - default_model_price + trial_30days_server_price + trial_30days_model_price)
                tax_trial_packagge +=  int(orders.amount_tax - default_server_tax - default_model_tax + trial_30days_server_tax + trial_30days_model_tax)

                
                #UPDATE ORDERS
                # price recalculation of sale order
                orders.update({
                    'original_amount_untaxed': amount_trial_package,
                    'original_amount_tax': tax_trial_packagge,
                    'original_amount_total': amount_trial_package + tax_trial_packagge,
                })

       
        # END CUSTOM CODE
        # We retrieve the token the user want to use to pay
        if not request.env['payment.token'].sudo().search_count([('id', '=', pm_id)]):
            return request.redirect('/shop/?error=token_not_found')

        # Create transaction
        vals = {'payment_token_id': pm_id, 'return_url': '/shop/payment/validate'}

        tx = order._create_payment_transaction(vals)
        PaymentProcessing.add_payment_transaction(tx)
        return request.redirect('/payment/process')

    # INHERIT
    # ADD NEW VALUE
    def _get_shop_payment_values(self, order, **kwargs):
        # CUSTOM CODE
        # GET PRODUCT OBJECT IN ORDER LINE
        categories = request.env['product.category'].search([('is_checkout_section','=','True')])
        sale_order = order
        data = []
        for category in categories:
            obj = {}
            obj['category_id'] = category.id
            obj['category_name'] = category.name
            product_arr = []
            for line in sale_order.website_order_line:
                if line.product_id.product_tmpl_id.categ_id.is_checkout_section and category.id == line.product_id.product_tmpl_id.categ_id.id:
                    o = {}
                    o['id']=  line.product_id.id
                    o['image'] = line.product_id.image_128
                    o['name'] = line.name_short
                    o['qty'] = line.product_uom_qty
                    o['categ_id'] = line.product_id.product_tmpl_id.categ_id.id
                    o['price_reduce_taxexcl'] = line.price_reduce_taxexcl
                    o['price_reduce_taxinc'] = line.price_reduce_taxinc
                    product_arr.append(o)
            obj['products'] = product_arr
            data.append(obj)

        # GET FIRST INVOICE PERCENT AND TRIAL DAYS 
        first_invoice_percent = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.first_invoice_percent')
        server_payment_term_id = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        section_label = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.section_label')
        trial_days = request.env['account.payment.term'].sudo().browse(int(server_payment_term_id)).line_ids.days
        # END CUSTOM CODE
        values = dict(
            website_sale_order=order,
            errors=[],
            partner=order.partner_id.id,
            order=order,
            payment_action_id=request.env.ref('payment.action_payment_acquirer').id,
            return_url= '/shop/payment/validate',
            bootstrap_formatting= True,
            # CUSTOM CODE
            data = data,
            categories = categories,        
            is_server = False,
            is_digital = False,
            is_checkout_section = False,
            is_normal = False,
            trial_days = trial_days,
            first_invoice_percent = first_invoice_percent,
            section_label = section_label,
            # END CUSTOM CODE
        )

        domain = expression.AND([
            ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', order.company_id.id)],
            ['|', ('website_id', '=', False), ('website_id', '=', request.website.id)],
            ['|', ('country_ids', '=', False), ('country_ids', 'in', [order.partner_id.country_id.id])]
        ])
        acquirers = request.env['payment.acquirer'].search(domain)

        values['access_token'] = order.access_token
        values['acquirers'] = [acq for acq in acquirers if (acq.payment_flow == 'form' and acq.view_template_id) or
                                    (acq.payment_flow == 's2s' and acq.registration_view_template_id)]
        values['tokens'] = request.env['payment.token'].search([
            ('acquirer_id', 'in', acquirers.ids),
            ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id)])

        if order:
            values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(order.amount_total, order.currency_id, order.partner_id.country_id.id)
        return values

    # INHERIT
    # SHOW PAYMENT PACKAGE WHEN HAVE SERVER PACKAGE IN ORDER LINE
    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order() 
        # redirection = self.checkout_redirection(order) or self.checkout_check_address(order)
        # if redirection:
        #     return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False

        # CUSTOM CODE
        # GET PAYMENT TERM OF SERVER PRODUCT
        server_payment_term_id = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        is_server_package = False
        for line in order.order_line:
            if line.product_id.product_tmpl_id.is_value_package:
                render_values['is_server'] = True
                is_server_package = True
            if line.product_id.product_tmpl_id.categ_id.is_digital_category:
                render_values['is_digital'] = True
            if line.product_id.product_tmpl_id.categ_id.is_checkout_section:
                render_values['is_checkout_section'] = True
            if not line.product_id.product_tmpl_id.is_value_package and not line.product_id.product_tmpl_id.categ_id.is_digital_category and not line.product_id.product_tmpl_id.categ_id.is_checkout_section:
                render_values['is_normal'] = True
        # UPDATE PAYMENT TERM OF SALE ORDER WHEN ORDER LINE HAVE SERVER PRODUCT 
        if is_server_package:
            order.update({
                'payment_term_id': int(server_payment_term_id),
            })
        else:
            order.update({
                'payment_term_id': 1,
            })
        # END CUSTOM CODE

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')

        return request.render("website_sale.payment", render_values)

   

        
    
        