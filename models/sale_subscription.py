# # -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from dateutil.relativedelta import TU, relativedelta
import datetime
from datetime import date, datetime
import time
import datetime
import random, string
from odoo.tools import format_date, float_compare
# from tkinter import *

import logging
_logger = logging.getLogger(__name__)

INTERVAL_FACTOR = {
    'daily': 30.0,
    'weekly': 30.0 / 7.0,
    'monthly': 1.0,
    'yearly': 1.0 / 12.0,
}

PERIODS = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}

class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'
    
    show_license_panel = fields.Boolean(string='Show License Panel', compute='_compute_show_license_panel', store=True, readonly=True)
    namespace = fields.Char(string="NameSpace", related="code")
    license_key = fields.Char(string="License Key", compute='_compute_license_key', store=True, readonly=True)
    uuid = fields.Char(string="UUID", readonly=True)
    domain = fields.Char(string="Domain")
    addons_repo = fields.Char(string="Addons Repo")
    dependencies = fields.Text(string="Dependencies", default=" ")
    is_extend = fields.Boolean("Extend", default = False)
    is_first_invoice_server_payment = fields.Boolean("is first invoice server payment", default = False)
    extend_date = fields.Many2one('account.payment.term', string='Force Extend Date', store = True)
    extend_date_by_calendar = fields.Date(string='Force Extend Date by Calendar', index=True, copy=False, default=fields.date.today())
    first_invoice_server_status = fields.Char("first invoice server status", readonly = True)
   
    

    # date_template_name = fields.Char('Template Name')
    # trial_days = fields.Char('Trial Days')
    # first_invoice_percent = fields.Char('First Invoice Percent')

    config = fields.Text(string='Config', readonly=True)

    # is_trial_version = True when server payment success (partial or paid)
    # IF is_trial_version == True -> license_state == running, enable end_trial_date, update recurring_next_invoice
    is_trial_version = fields.Boolean('Trial Version')
   

    end_trial_date = fields.Date(string='End Trial Date', compute="_compute_trial_date", store=True)
    #recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.", compute="onchange_recurring_next_date")
    license_state = fields.Selection(selection=[
        ('pending','Pending'),
        ('running','Running'),
        ('closed','Closed'),
        ('deleted','Deleted')
        ], readonly=True, compute="_compute_license_state")
    hidden_state = fields.Selection(selection=[
        ('pending','Pending'),
        ('running','Running'),
        ('closed','Closed'),
        ('deleted','Deleted')
        ], readonly=True, default='pending')
    # SEVER BUTTON
    def button_create_server(self):
        for rec in self:
            rec.hidden_state = 'running'
    # def button_redeploy_server(self):
    #     for rec in self:
    #         rec.hidden_state = 'running'
    def button_start_server(self):
        for rec in self:
            rec.hidden_state = 'running'
    def button_stop_server(self):
        for rec in self:
            rec.hidden_state = 'closed'
    #def button_delete_server(self):
        # for rec in self:
        #     rec.license_state = 'deleted'
        
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Delete server',
        #     'views': [(self.env.ref('license_management.delete_server_form').id, 'form')],
        #     'res_model': 'sale.subscription.wizard.delete.server',
        #     'target': 'new',
        # }
    # ONCHANGE LICENSE STATE UP TO DATE
    @api.depends('is_extend', 'extend_date_by_calendar','hidden_state','is_trial_version','end_trial_date','stage_id')
    def _compute_license_state(self):
        # self.is_partial = False
        invoices = self.env['account.move'].search(['&',('invoice_line_ids.subscription_id', '=', self.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1)
        _logger.debug("=======================")
        _logger.debug("=======================")
        _logger.debug("=======================")
        _logger.debug("=======================")
        _logger.debug(invoices.payment_state)
        # invoices = self.env['account.move'].search([('invoice_line_ids.subscription_id', 'in', self.ids)])
        for rec in self:
            today = date.today()              
            # WHEN ENABLE EXTEND DATE
            if rec.is_extend and rec.extend_date_by_calendar < today:
                if rec.hidden_state == 'deleted':
                    rec.license_state = 'deleted'
                else:
                    rec.license_state = 'closed'                                                         
            elif rec.is_extend and rec.extend_date_by_calendar >= today:
                state = rec.hidden_state
                rec.license_state = state
            # WHEN DISABLE EXTEND DATE AND UNPAID
            if not rec.is_extend and not rec.is_trial_version:   
                if rec.recurring_next_date < today:                         
                    if rec.hidden_state == 'deleted':
                        rec.license_state = 'deleted'
                    else:
                        rec.license_state = 'closed'                                                                    
                elif rec.recurring_next_date >= today:
                    state = rec.hidden_state
                    rec.license_state = state     
            # WHEN DISABLE EXTEND DATE AND FIRST INVOICE SERVER'S STATUS IS PARTIAL
            elif not rec.is_extend and rec.is_trial_version and invoices.payment_state == 'partial':
                if rec.recurring_next_date < today or rec.end_trial_date < today:
                    if rec.hidden_state == 'deleted':
                        rec.license_state = 'deleted'
                    else:
                        rec.license_state = 'closed'                                                                 
                elif rec.recurring_next_date >= today and rec.end_trial_date >= today:
                    state = rec.hidden_state
                    rec.license_state = state
            # WHEN DISABLE EXTEND DATE AND FIRST INVOICE SERVER'S STATUS IS PAID
            elif not rec.is_extend and rec.is_trial_version and invoices.payment_state == 'paid':
                if rec.recurring_next_date < today:
                    if rec.hidden_state == 'deleted':
                        rec.license_state = 'deleted'
                    else:
                        rec.license_state = 'closed'                                                                    
                elif rec.recurring_next_date >= today and rec.end_trial_date >= today or rec.end_trial_date < today:
                    state = rec.hidden_state
                    rec.license_state = state
            elif not rec.is_extend and rec.is_trial_version and invoices.payment_state != 'paid' and invoices.payment_state != 'partial':
                state = rec.hidden_state
                rec.license_state = state

            # CLOSED SUB -> CLOSED SERVER
            if rec.stage_id.id == 3:
                rec.license_state = 'closed' 
                    

        
    # LICENSE STATE UP TO DATE
    # def write(self, vals):         
    #     res = super(SaleSubscription, self).write(vals)   
    #     today = date.today()     
    #     if vals.get('extend_date_by_calendar'):
    #         self.convert_extend_date_by_calendar = datetime.datetime.strptime(vals.get('extend_date_by_calendar'), '%Y-%m-%d')
    #         if self.convert_extend_date_by_calendar < today:
    #             self.license_state = 'closed'
    #         elif self.convert_extend_date_by_calendar > today:
    #             self.license_state = 'running'    
    #     return res
           
            
                
                
    #LICENSE KEY
    # @api.depends('recurring_invoice_line_ids.product_id')
    @api.depends('date_start')
    def _compute_license_key(self):
        for subscription in self:
            date_to_string = fields.Date.from_string(subscription.date_start).strftime('%Y%m%d')
            r = ''.join(random.sample(string.ascii_uppercase, 15))
            subscription.license_key = '%s%s%s' % (subscription.code, date_to_string, r) 
            
    @api.depends('recurring_invoice_line_ids.product_id','recurring_invoice_line_ids.quantity')
    def _compute_show_license_panel(self):
        for subscription in self:
            subscription.show_license_panel = False
            # arr = []
            for line in subscription.recurring_invoice_line_ids:
                # arr.append(line.product_id.product_tmpl_id.is_value_package)
                #LIMIT PRODUCT IN ODER LINES
                if line.product_id.product_tmpl_id.is_value_package:
                    subscription.show_license_panel = True
                    #CONFIG OF PRODUCT(ram, cpu, disk)
                    str = ''
                    # get current server package (server package & quantity > 0)
                    current_server_package = self.env['sale.subscription.line'].search(['&',('analytic_account_id', '=', subscription.id),('product_id.product_tmpl_id.is_value_package','=',True),('quantity','>',0)], order="id desc",limit=1)
                    for x in current_server_package.product_id.product_template_attribute_value_ids:
                        str += '\n%s: %s' % (x.attribute_id.name, x.product_attribute_value_id.name) 

                    subscription.config = str.strip()
             #RAISE ERROR IF HAVE MORE THAN 1 SERVER PACKAGE
            # if arr.count(True) > 1:
            #     # sale_order = self.env['sale.order'].search([('order_line.subscription_id', 'in', self.ids)], order="id desc", limit=1)
            #     # for sale_order in subscription.sale_order:
            #     #     for line in sale_order.order_line:
            #     #         if line.product_id.product_tmpl_id.is_value_package:
            #     #             line.unlink()
            #     raise UserError(_("Server package is exists in order lines."))

               
    # CUSTOM DATETIME
    @api.depends('date_start', 'is_trial_version')
    def _compute_trial_date(self):   
        
        server_payment_term_id = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.server_payment_term_id')
        server_payment_term_days = self.env['account.payment.term'].search([('id','=',server_payment_term_id)]).line_ids.days
        # default_trial_days = self.env['ir.config_parameter'].sudo().get_param('sale_subscription.trial_days')
       
        for rec in self:      
            # get first invoice server
            invoices = self.env['account.move'].search(['&',('invoice_line_ids.subscription_id', '=', rec.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1) 
            # get first invoice server status
            rec.first_invoice_server_status = invoices.payment_state
            
            end_day = date.today() + relativedelta(days =+ int(server_payment_term_days))
           
            
            #set End trial date

            rec.end_trial_date = end_day if rec.is_trial_version else False   

            if rec.is_trial_version and (invoices.payment_state == 'partial' or invoices.payment_state == 'paid') and not rec.is_first_invoice_server_payment:
                rec.recurring_next_date += relativedelta(days =+ int(server_payment_term_days))
                rec.is_first_invoice_server_payment = True
            elif rec.is_trial_version and (invoices.payment_state == 'partial' or invoices.payment_state == 'paid') and rec.is_first_invoice_server_payment:
                rec.recurring_next_date = rec.recurring_next_date
            elif rec.is_trial_version and invoices.payment_state != 'paid' and invoices.payment_state != 'partial':
                rec.recurring_next_date = rec.recurring_next_date

            # if rec.is_trial_version and invoices.payment_state == 'partial':
            #     rec.recurring_next_date += relativedelta(days =+ int(invoices.invoice_payment_term_id.line_ids.days))
            # elif rec.is_trial_version and invoices.payment_state == 'paid':
            #     rec.recurring_next_date += relativedelta(days =+ int(invoices.invoice_payment_term_id.line_ids.days)) + relativedelta(years =+ 1)
            # elif rec.is_trial_version and invoices.payment_state != 'paid' and rec.is_trial_version and invoices.payment_state != 'partial':
            #     rec.recurring_next_date = rec.recurring_next_date
    
    # @api.onchange('date_start', 'template_id', 'recurring_invoice_line_ids.product_id')
    # def onchange_recurring_next_date(self):
    #     if self.date_start and self.recurring_rule_boundary == 'limited' and self.recurring_rule_type == 'yearly' and self.show_license_panel:
    #         self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval}) + relativedelta(days =+ 31)
    #     elif self.date_start and self.recurring_rule_boundary == 'limited':
    #         self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval})           
    #     elif self.date_start and self.recurring_rule_boundary == 'unlimited':
    #         self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_interval})

   
    # @api.onchange('date_start', 'template_id', 'recurring_invoice_line_ids.product_id')
    # def onchange_date_start(self):
    #     if self.date_start and self.recurring_rule_boundary == 'limited' and self.recurring_rule_type == 'yearly' and self.show_license_panel:
    #         self.date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval}) + relativedelta(days =+ 31)
    #     elif self.date_start and self.recurring_rule_boundary == 'limited':
    #         self.date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval})         
    #     else:
    #         self.date = False

#--------------------------------------------------------------------
    @api.onchange('date_start', 'template_id', 'recurring_invoice_line_ids.product_id', 'is_trial_version')
    def onchange_recurring_next_date(self):
        pass
        # if self.date_start and self.recurring_rule_boundary == 'limited' and self.is_trial_version and self.recurring_rule_type != 'monthly':
        #     self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
        #         PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval}) + relativedelta(days =+ 31)
        # elif self.date_start and self.recurring_rule_boundary == 'limited':
        #     self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
        #         PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval})           
        # elif self.date_start and self.recurring_rule_boundary == 'unlimited' and self.is_trial_version:
        #     self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
        #         PERIODS[self.recurring_rule_type]: self.template_id.recurring_interval}) + relativedelta(days =+ 31)
        # elif self.date_start and self.recurring_rule_boundary == 'unlimited':
        #     self.recurring_next_date = fields.Date.from_string(self.date_start) + relativedelta(**{
        #         PERIODS[self.recurring_rule_type]: self.template_id.recurring_interval})



    # INHERIT FROM sale_subscription's model
    # @api.onchange('date_start', 'template_id', 'recurring_invoice_line_ids.product_id', 'is_trial_version')
    # def onchange_date_start(self):
    #     if self.date_start and self.recurring_rule_boundary == 'limited' and self.is_trial_version and self.recurring_rule_type != 'monthly':
    #         self.date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval}) + relativedelta(days =+ 31)
    #     elif self.date_start and self.recurring_rule_boundary == 'limited':
    #         self.date = fields.Date.from_string(self.date_start) + relativedelta(**{
    #             PERIODS[self.recurring_rule_type]: self.template_id.recurring_rule_count * self.template_id.recurring_interval})         
    #     else:
    #         self.date = False
          
# class SaleSubscriptionDateTemplate(models.Model):
#     _name = 'sale.subscription.datetemplate'
#     _description = 'Subscription Test'

#     trial_days = fields.Char('Trial Days')
#     first_invoice_percent = fields.Char('First Invoice Percent')


    def return_first_invoice_server(self):
        invoices = self.env['account.move'].search(['&',('invoice_line_ids.subscription_id', '=', self.id),('invoice_line_ids.product_id.product_tmpl_id.is_value_package','=',True)], order="id asc",limit=1)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [[False, "form"]],
            "res_id": invoices.id,
        }
    
    
                       
                   
                   




        

       
    

    


    
    


    


    

       
       
       

    