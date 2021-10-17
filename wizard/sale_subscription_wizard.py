# -*- coding: utf-8 -*-
import datetime
from datetime import date
from typing import Sequence
from odoo import models, fields, api, _
import json
from odoo.exceptions import UserError
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)
class SaleSubscriptionWizard(models.TransientModel):
    _inherit = 'sale.subscription.wizard'
   
    def _default_subscription(self):
        return self.env['sale.subscription'].browse(self._context.get('active_id'))

    subscription_id = fields.Many2one('sale.subscription', string="Subscription", required=True, default=_default_subscription, ondelete="cascade")
    option_lines = fields.One2many('sale.subscription.wizard.option', 'wizard_id', string="Options")
    date_from = fields.Date("Start Date", default=fields.Date.today,
                            help="The discount applied when creating a sales order will be computed as the ratio between "
                                 "the full invoicing period of the subscription and the period between this date and the "
                                 "next invoicing date.")

    def create_sale_order(self):
        self = self.with_company(self.subscription_id.company_id)
        fpos = self.env['account.fiscal.position'].get_fiscal_position(
            self.subscription_id.partner_id.id)
        #create sale order
        sale_order_obj = self.env['sale.order']
        team = self.env['crm.team']._get_default_team_id(user_id=self.subscription_id.user_id.id)
        new_order_vals = {
            'partner_id': self.subscription_id.partner_id.id,
            'analytic_account_id': self.subscription_id.analytic_account_id.id,
            'team_id': team and team.id,
            'pricelist_id': self.subscription_id.pricelist_id.id,
            'payment_term_id': self.subscription_id.payment_term_id.id,
            'fiscal_position_id': fpos.id,
            'subscription_management': 'upsell',
            'origin': self.subscription_id.code,
            'company_id': self.subscription_id.company_id.id,
            
        }
        # we don't override the default if no payment terms has been set on the customer
        if self.subscription_id.partner_id.property_payment_term_id:
            new_order_vals['payment_term_id'] = self.subscription_id.partner_id.property_payment_term_id.id
        order = sale_order_obj.create(new_order_vals)
        order.message_post(body=(_("This upsell order has been created from the subscription ") + " <a href=# data-oe-model=sale.subscription data-oe-id=%d>%s</a>" % (self.subscription_id.id, self.subscription_id.display_name)))
        for line in self.option_lines:
            self.subscription_id.partial_invoice_line(order, line, date_from=self.date_from)
        order.order_line._compute_tax_id()
        # CUSTOM CODE
        #CREATE SECTION DOWMPAYMENT WHEN UPSELL SERVER  
        order_line_obj = self.env['sale.order.line'] 
        #get current server package (last package)
        current_server_package = self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', self.subscription_id.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
        #check upsell server package
        is_server_package_upsell = self.env['sale.order.line'].search(['&',('order_id', '=', order.id),('product_id.product_tmpl_id.is_value_package','=',True)])
        #only create down payment when upselling server products and current subscription has server product too 
        if current_server_package and is_server_package_upsell:
            # UPDATE payment_term_id WHEN UPSELL SERVER PACKAGE
            order.update({
            'payment_term_id': 1,
            })
            ratio, message = self.subscription_id._partial_recurring_invoice_ratio(date_from=date.today())
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
                'subscription_id': self.subscription_id.id,         
                'discount': _discount,
                'is_downpayment': True,         
                'product_uom_qty': -1 * current_server_package.quantity, 
                'product_uom': current_server_package.uom_id.id,            
            }
            order_line_obj.create(section)
            order_line_obj.create(old_server)
            order.message_post(body=(_("A Down payment has been created from the Order ") + " <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>" % (order.id, order.name)))
        # END CUSTOM CODE
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order.id,
        }
class SaleSubscriptionWizardOption(models.TransientModel):
    _inherit = "sale.subscription.wizard.option"
    
    # product_id = fields.Many2one('product.product', required=True, domain="[('product_tmp_id.id', '=', 32)]", ondelete="cascade")
    current_server_sale_price = fields.Float(compute= "_compute_current_server_sale_price")
    product_id_domain = fields.Char(
       compute="_compute_product_id_domain",
       readonly=True,
       store=False,
   )
    product_id = fields.Many2one('product.product', required=True, ondelete="cascade")


    #GET CURRENT SALE_PRICE OF SERVER
    @api.depends("product_id")
    def _compute_current_server_sale_price(self):
        current_server_package_sale_price = self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', self.wizard_id.subscription_id.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
        if current_server_package_sale_price:
            current_sale_price = current_server_package_sale_price.product_id.sale_price
            self.current_server_sale_price = current_sale_price
        else:
            self.current_server_sale_price = -1

    #DOMAIN FILTER
    @api.onchange('product_id')
    def _onchange_product_id_domain(self):       
        for rec in self:
            domain = expression.OR([
                    ['&', ('is_server', '=', True), ('sale_price', '>', rec.current_server_sale_price),('digital_package_value_id','!=', False)],
                    ['&', ('is_server', '!=', True), ('recurring_invoice', '=', True)],
                ])
            return {'domain': {'product_id': domain}}
            # return {'domain': {'product_id': ['|','&',('is_server', '=', True),('sequence','>',rec.current_server_sequence),'&',('is_server', '!=', True),('recurring_invoice', '=', True)]}}
            
    
