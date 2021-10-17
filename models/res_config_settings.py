# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    section_label = fields.Char(default=lambda self: self.get_default_label(), string="Default Section Label") 
    first_invoice_percent = fields.Integer(default=10, string="Default first invoice percent (Percent)")
    server_payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms')
    

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        label = ICPSudo.get_param('sale_subscription.section_label')  
        percents = ICPSudo.get_param('sale_subscription.first_invoice_percent')
        term_id = ICPSudo.get_param('sale_subscription.server_payment_term_id')
       
        res.update(
            section_label = label,         
            first_invoice_percent = percents,
            server_payment_term_id = int(term_id),
        )
        return res
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('sale_subscription.section_label', self.section_label)   
        self.env['ir.config_parameter'].set_param('sale_subscription.first_invoice_percent', self.first_invoice_percent)
        self.env['ir.config_parameter'].set_param('sale_subscription.server_payment_term_id', self.server_payment_term_id.id)
        return res
    
    def get_default_label(self):
        default_label = "Normal Product"
        return default_label
