# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import datetime
from datetime import date

import logging
_logger = logging.getLogger(__name__)

class Website(http.Controller):

    # CUSTOM CODE
    @http.route(['/pricing'], type='http', auth="public", website=True)
    def pricing(self, **kw):
        order = request.website.sale_get_order()
        # GET OBJECT OF SERVER PACKAGE
        product_tmpl_id = request.env['product.template'].sudo().search([('is_value_package', '=', True)], limit=1).id
        # products = request.env['product.product'].sudo().search(['&',('product_tmpl_id', '=', product_tmpl_id),('digital_package_value_id','!=',False)])
        products = request.env['product.product'].sudo().search([('product_tmpl_id', '=', product_tmpl_id)])
        # product_data = []
        # for product in products:
        #     price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
        #     obj = {}
        #     if product.digital_package_value_id:
        #         for p in product.product_template_attribute_value_ids:
        #             obj['product_id'] = product.id
        #             obj[p.attribute_id.name] = p.name
        #             obj['price'] = p.product_tmpl_id.list_price + price_extra
        #         product_data.append(obj)

        digital_package_values = request.env['product.digitalpackage.value'].sudo().search([('is_server','=', True)])
        data = []
        for digital_package_value in digital_package_values:
            object = {}
            object['digital_package_value_id'] = digital_package_value.id
            object['digital_package_value_name'] = digital_package_value.name
            product_arr = []
            for product in products:
                # price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
                o = {}
                if product.digital_package_value_id.id == digital_package_value.id:                  
                    for p in product.product_template_attribute_value_ids:    
                        combination_info = product._get_combination_info_variant(pricelist=order.pricelist_id)                  
                        o['product_id']=  product.id
                        o['digital_package_value_id'] = product.digital_package_value_id.id
                        o[p.attribute_id.name] = p.name
                        # o['price'] = p.product_tmpl_id.list_price + price_extra                       
                        o['price'] = combination_info['price']              
                    product_arr.append(o)
            object['products'] = product_arr
            data.append(object)

        # GET FIRST INVOICE PERCENT AND TRIAL DAYS 
        first_invoice_percent = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.first_invoice_percent')
        server_payment_term_id = request.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        trial_days = request.env['account.payment.term'].sudo().browse(int(server_payment_term_id)).line_ids.days
        # GET CURRENT WEBSITE
        website = request.env['website'].get_current_website()
        values = {
            # 'products': product_data,
            'trial_days': trial_days,
            'first_invoice_percent': first_invoice_percent,
            'website':website,
            'uom_id': products.uom_id,
            'data':data,
        }

       
        return request.render("license_management.pricing", values)

  

    
      
    

           
    
