# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


from werkzeug.urls import url_encode


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # DEFAULT PAYMENT TERM
    # @api.model
    # def default_get(self, fields):
    #     server_payment_term_id = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
    #     res = super(SaleOrder, self).default_get(fields)
    #     res['payment_term_id'] = int(server_payment_term_id)
    #     return res

    #ADD NEW FIELD NAMED show_create_invoice_package
    # show_create_invoice_package = fields.Boolean(string='Show Create Invoice Package', compute='_compute_show_create_invoice_package', store=True, readonly=True)
    # @api.depends('order_line.product_id')
    # def _compute_show_create_invoice_package(self):
    #     for order in self:
    #         order.show_create_invoice_package = False
    #         for line in order.order_line: 
    #             if line.product_id.product_tmpl_id.is_value_package:
    #                 order.show_create_invoice_package = True

    #ADD NEW TABLE NAMED amount_untaxed_first_invoice AND amount_total_first_invoice
    amount_untaxed_first_invoice = fields.Monetary(string='Untaxed Fisrt Invoice Amount', store=True, readonly=True, compute='_amount_all')
    amount_total_first_invoice = fields.Monetary(string='Total Fisrt Invoice Amount', store=True, readonly=True, compute='_amount_all')
    amount_tax_first_invoice = fields.Monetary(string='Tax Fisrt Invoice Amount', store=True, readonly=True, compute='_amount_all')

    # ADD NEW COLUMN SHOW ORIGINAL AMOUNT IN QUOTATION IF USER SELECTED TRIAL 30 DAYS 
    original_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all')
    original_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    original_amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    is_trial = fields.Boolean("is trial", compute='_amount_all', store=True)
    # when upgrade package in sale_subscription -> caculate amount left of old package (caculate in sale_subscription_portal.py) 
    package_amount_left = fields.Monetary("amount upgrade", default = 0)
    # ADD NEW SELECTION FOR PAYMENT 
    # select_payment_package = fields.Selection(selection=[('full', 'FULLY PAYMENT + 30 DAYS'),
    #     ('trial','PAY 10% AND TRIAL IN 30DAYS')],
    #     default='full', required=True, string='Select Payment Package',
    #     )

    # @api.onchange('order_line.product_id','')
    #INHERIT FUNCTION
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        first_invoice_percent = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.first_invoice_percent')
        for order in self:
            order.is_trial = False
            original_amount_untaxed = original_amount_tax = 0.0
            amount_untaxed_first_invoice = amount_tax_first_invoice = 0.0
            default_server_price = trial_30days_server_price = default_server_tax = trial_30days_server_tax = 0.0
            default_model_price = trial_30days_model_price = default_model_tax = trial_30days_model_tax = 0.0
            for line in order.order_line:
                # GET PRICE OF SERVER PRODUCT IN sale_order_line
                if line.product_id.product_tmpl_id.is_value_package:
                    order.is_trial = True
                    #default price
                    default_server_price += line.price_subtotal
                    #10% price
                    trial_30days_server_price += (line.price_subtotal/100*int(first_invoice_percent))
                    #default tax
                    default_server_tax += line.price_tax
                    #10% tax
                    trial_30days_server_tax += (line.price_tax/100*int(first_invoice_percent))

                # GET PRICE OF DIGITAL PRODUCT IN sale_order_line
                if line.product_id.product_tmpl_id.categ_id.is_digital_category:
                    order.is_trial = True
                    default_model_price += line.price_subtotal
                    #10% price
                    trial_30days_model_price += (line.price_subtotal/100*int(first_invoice_percent))
                    #default tax
                    default_model_tax += line.price_tax
                    #10% tax
                    trial_30days_model_tax += (line.price_tax/100*int(first_invoice_percent))
            # GET PRICE AND TAX OF FULLPAYMENT
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

             # GET PRICE AND TAX OF TRIAL 30DAYS
            amount_untaxed_first_invoice += int(amount_untaxed - default_server_price - default_model_price + trial_30days_server_price + trial_30days_model_price)
            amount_tax_first_invoice += int(amount_tax - default_server_tax  - default_model_tax + trial_30days_server_tax + trial_30days_model_tax)
            # GET PRICE TO SHOW IN QUOTATION
            original_amount_untaxed += amount_untaxed 
            original_amount_tax += amount_tax
            #UPDATE ORDERS
            order.update({
                # THESE VALUES WILL SHOW IN WEBSITE  
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
                # THESE VALUES WILL SHOW IN WEBSITE  
                'amount_untaxed_first_invoice': amount_untaxed_first_invoice,
                'amount_tax_first_invoice': amount_tax_first_invoice,            
                'amount_total_first_invoice': amount_untaxed_first_invoice + amount_tax_first_invoice,
                # THESE VALUES WILL SHOW IN QUOTATION
                'original_amount_untaxed': original_amount_untaxed,
                'original_amount_tax': original_amount_tax,
                # 'original_amount_total': original_amount_untaxed + original_amount_tax - order.package_amount_left,
                'original_amount_total': original_amount_untaxed + original_amount_tax,
            })

    # INHERIT
    # DUE DATE DEFAULT 30 DAYS WHEN ORDER HAVE SERVER PRODUCT
    def _prepare_invoice(self):
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))
        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'invoice_user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        # CUSTOM CODE
        # get_today = fields.Date.today()
       
        # for order in self:
        #     for line in order.order_line:
        #         if line.product_id.product_tmpl_id.is_value_package:
        #             invoice_vals.update({
        #                'invoice_date': get_today,                
        #         })
        # END CUSTOM CODE
        return invoice_vals

    # INHERIT
    # SET DEFAULT payment_term_id by config when create sale order
    @api.model
    def create(self, vals):
        # CUSTOM CODE
        # server_payment_term_id = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        # vals['payment_term_id'] = int(server_payment_term_id)
        # END CUSTOM CODE
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.order', sequence_date=seq_date) or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist.id)
        result = super(SaleOrder, self).create(vals)
        # _logger.debug("=============vals==============")
        # _logger.debug("=============vals==============")
        # _logger.debug("=============vals==============")
        # _logger.debug("=============vals==============")
        # _logger.debug("=============vals==============")
        # _logger.debug(result)
        # _logger.debug(self)
        # sale_order = self.env['sale.order'].search([('id','=',result.id)])
        # is_server_package = False
        # for line in sale_order.order_line:
        #     if line.product_id.product_tmpl_id.is_value_package:
        #         is_server_package = True           
        # if is_server_package:
        #     sale_order.update({
        #             'payment_term_id':2,
        #         })
        return result
        
    

    
        
    # INHERIT
    # CHANGE PAYMENT TRANSACTION AMOUNT WHEN PAYMENT ON WEBSITE
    def _create_payment_transaction(self, vals):
        '''Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current sales orders fields (e.g. the partner or the currency).
        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        '''
        # Ensure the currencies are the same.
        currency = self[0].pricelist_id.currency_id
        if any(so.pricelist_id.currency_id != currency for so in self):
            raise ValidationError(_('A transaction can\'t be linked to sales orders having different currencies.'))

        # Ensure the partner are the same.
        partner = self[0].partner_id
        if any(so.partner_id != partner for so in self):
            raise ValidationError(_('A transaction can\'t be linked to sales orders having different partners.'))

        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = vals.get('acquirer_id')
        acquirer = False
        payment_token_id = vals.get('payment_token_id')

        if payment_token_id:
            payment_token = self.env['payment.token'].sudo().browse(payment_token_id)

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(acquirer_id)
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise ValidationError(_('Invalid token found! Token acquirer %s != %s') % (
                    payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise ValidationError(_('Invalid token found! Token partner %s != %s') % (
                    payment_token.partner.name, partner.name))
            else:
                acquirer = payment_token.acquirer_id

        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise ValidationError(_('A payment acquirer is required to create a transaction.'))

        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(acquirer_id)

        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise ValidationError(_('A journal must be specified for the acquirer %s.', acquirer.name))

        if not acquirer_id and acquirer:
            vals['acquirer_id'] = acquirer.id
        # CUSTOM CODE
        amount = sum(self.mapped('original_amount_total'))
        vals.update({
            'amount': amount,
            'currency_id': currency.id,
            'partner_id': partner.id,
            'sale_order_ids': [(6, 0, self.ids)],
            'type': self[0]._get_payment_type(vals.get('type')=='form_save'),
        })
        # END CUSTOM CODE

        self.with_context(send_email=True).action_confirm()


        transaction = self.env['payment.transaction'].create(vals)

        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()

        return transaction

    
    # def update_prices(self):
    #     self.ensure_one()
    #     lines_to_update = []
    #     for line in self.order_line.filtered(lambda line: not line.display_type):
    #         product = line.product_id.with_context(
    #             partner=self.partner_id,
    #             quantity=line.product_uom_qty,
    #             date=self.date_order,
    #             pricelist=self.pricelist_id.id,
    #             uom=line.product_uom.id
    #         )
    #         price_unit = self.env['account.tax']._fix_tax_included_price_company(
    #             line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)
    #         if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
    #             discount = max(0, (price_unit - product.price) * 100 / price_unit)
    #         else:
    #             discount = 0 + 60
    #         lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': 60}))
    #     _logger.debug("==========discount=========")
    #     _logger.debug("===================")
    #     _logger.debug("===================")
    #     _logger.debug("===================")
    #     _logger.debug(price_unit)
    #     _logger.debug(product.price)
    #     self.update({'order_line': lines_to_update})
    #     self.show_update_pricelist = False
    #     self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))

    # UPDATE PAYMENT TERM WHEN CHANGE ORDER_LINE
    @api.onchange('order_line')
    def onchange_order_line(self):
        is_server_package = False
        server_payment_term_id = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        for line in self.order_line:
            if line.product_id.product_tmpl_id.is_value_package:
                    is_server_package = True
            if is_server_package:
                self.update({
                    'payment_term_id': int(server_payment_term_id)
                })
            else:
                self.update({
                    'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
                })

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'  

    # INHERIT
    
    # return True when upselling server products and current subscription has server product too (see in sale_subscription_wizard)
    is_server_upsell_downpayment = fields.Boolean("is server upsell down payment")
    # CONFIG NEW PACKAGE WHEN UP SELL
    def _prepare_subscription_line_data(self):
        """Prepare a dictionnary of values to add lines to a subscription."""
        values = list()
        for line in self:
            # CUSTOM CODE
            current_server_package = self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', line.subscription_id.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
            if line.product_id.product_tmpl_id.is_value_package and current_server_package:
                new_package_qty = 0
            else:
                new_package_qty = line.product_uom_qty
            # END CUSTOM CODE
            values.append((0, False, {
                'product_id': line.product_id.id,
                'name': line.name,
                # CUSTOM CODE
                'quantity': new_package_qty,
                # END CUSTOM CODE
                'uom_id': line.product_uom.id,
                'price_unit': line.price_unit,
                'discount': line.discount if line.order_id.subscription_management != 'upsell' else False,
            }))
        return values

    # INHERIT
    # CONFIG OLD PACKAGE WHEN UP SELL
    def _update_subscription_line_data(self, subscription):
        """Prepare a dictionnary of values to add or update lines on a subscription."""
        values = list()
        dict_changes = dict()
        for line in self:

            sub_line = subscription.recurring_invoice_line_ids.filtered(
                lambda l: (l.product_id, l.uom_id, l.price_unit) == (line.product_id, line.product_uom, line.price_unit)
            )
            if sub_line:
                # We have already a subscription line, we need to modify the product quantity
                if len(sub_line) > 1:
                    # we are in an ambiguous case
                    # to avoid adding information to a random line, in that case we create a new line
                    # we can simply duplicate an arbitrary line to that effect
                    sub_line[0].copy({'name': line.display_name, 'quantity': line.product_uom_qty})
                else:
                    dict_changes.setdefault(sub_line.id, sub_line.quantity)
                    # upsell, we add the product to the existing quantity
                    # CUSTOM CODE
                    if line.product_id.product_tmpl_id.is_value_package and line.product_uom_qty < 0:
                        dict_changes[sub_line.id] += 0                     
                    else:
                        dict_changes[sub_line.id] += line.product_uom_qty                  
                    # END CUSTOM CODE
            else:
                # we create a new line in the subscription: (0, 0, values)
                values.append(line._prepare_subscription_line_data()[0])

        values += [(1, sub_id, {'quantity': dict_changes[sub_id]}) for sub_id in dict_changes]
        return values

    

    
    
  
    

   
    

    