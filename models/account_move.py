# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
     
   
    # package_amount_left = fields.Monetary("Old Package Amount Left", compute='_compute_amount', store=True)
    # test = fields.Char("Test", compute='_compute_amount')
    # INHERIT
    def action_invoice_paid(self):
        # OVERRIDE
        res = super(AccountMove, self).action_invoice_paid()
       
        for invoice in self.filtered(lambda move: move.is_invoice()):
            for line in invoice.invoice_line_ids:
                for sale_line in line.sale_line_ids:     
                    #RUN SERVER AFTER PAYMENT SUCCESS
                    order_line = self.env['sale.order.line'].search([('order_id','=',sale_line.order_id.id)])
                    # check is server upsell downpayment and check server payment success
                    is_server_upsell_downpayment = False
                    is_server_payment = False
                    for o_line in order_line:
                        if o_line.is_server_upsell_downpayment:
                            is_server_upsell_downpayment = True   
                        if o_line.product_id.product_tmpl_id.is_value_package:
                            is_server_payment = True
                    # server payment success -> state = run -> disable force extend 
                    if is_server_payment:        
                        self.env['sale.subscription'].search([('id','=',order_line.subscription_id.id)]).write({'hidden_state':'running', 'is_trial_version':'True','is_extend': False})

                    # UPDATE QUANTITY SERVER PACKAGE WHEN UPSELL                                         
                    # diable old server package and include qty for new server package 
                    if is_server_upsell_downpayment:
                        # get old server package
                        current_server_package = self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', order_line.subscription_id.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
                        current_server_package.write({'quantity':0})
                        # get new server package
                        new_package_order_line = self.env['sale.order.line'].search(['&',('order_id','=',sale_line.order_id.id),('product_id.product_tmpl_id.is_value_package','=',True)], order="id asc", limit=1)
                        new_package_qty = new_package_order_line.product_uom_qty
                        self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', order_line.subscription_id.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','=',0)], order="id desc",limit=1).write({'quantity':new_package_qty})
                    
        return res

    # INHERIT
    # RUN SERVER WHEN payment_state == 'partial'
    def _compute_amount(self):        
        for move in self:
            # line = self.env['account.move.line'].sudo().search([('move_id','=',move.id)],limit=1).id
            # order_line = self.env['sale.order.line'].sudo().search([('invoice_lines','=',line)],limit=1)
            # package_amount_left = order_line.order_id.package_amount_left

            # move.package_amount_left = round(package_amount_left *-1)
        
            # move.test = package_amount_left
            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            
            
            
            currencies = move._get_lines_onchange_currency().currency_id

            for line in move.line_ids:
                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            # move.amount_total = sign * (total_currency - move.package_amount_left if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            # move.amount_residual = -sign * (total_residual_currency + move.package_amount_left if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies or move.company_id.currency_id

            # Compute 'payment_state'.
            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

            if move.is_invoice(include_receipts=True) and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()
                elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                    new_pmt_state = 'partial'

            if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

                # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                    new_pmt_state = 'reversed'

            # CUSTOM CODE
            if new_pmt_state == 'partial':
                 for invoice in self.filtered(lambda move: move.is_invoice()):
                    for line in invoice.invoice_line_ids:
                        for sale_line in line.sale_line_ids:
                            # RUN SERVER WHEN payment_state == 'partial'
                            order_line = self.env['sale.order.line'].search([('order_id','=',sale_line.order_id.id)])
                            self.env['sale.subscription'].search([('id','=',order_line.subscription_id.id)]).write({'hidden_state':'running', 'is_trial_version':'True'})      
            # END CUSTOM CODE

            move.payment_state = new_pmt_state

    #CHANGE DATE OF NEXT INVOICE BY DUE DATE
    # @api.onchange('invoice_payment_term_id')
    # def recurring_invoive_by_invoice_payment_term_id(self):
    #     for move in self:
    #     #     if move.invoice_payment_term_id.id == 2:
    #         for invoice in self.filtered(lambda move: move.is_invoice()):
    #             for line in invoice.invoice_line_ids:
    #                 for sale_line in line.sale_line_ids:
    #                     order_line = self.env['sale.order.line'].search([('order_id','=',sale_line.order_id.id)])
    #                     for sub in order_line.subscription_id:
    #                         # default_trial_days = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.trial_days')
    #                         # end_day = date.today() + relativedelta(days =+ int(move.invoice_payment_term_id.line_ids.days))
    #                         # sub.recurring_next_date =  end_day + relativedelta(days =+ 15) 
    #                         sub.recurring_next_date = date.today() + relativedelta(days =+ int(move.invoice_payment_term_id.line_ids.days))

            