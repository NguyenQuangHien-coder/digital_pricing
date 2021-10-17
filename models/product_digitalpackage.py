# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class ProductDigitalPackage(models.Model):
    _name = "product.digitalpackage"
    _order = 'sequence, id'
    _description = "Product Digital Package"
    
    name = fields.Char('Digital Package', required=True, translate=True)
    value_ids = fields.One2many('product.digitalpackage.value', 'digital_package_id', 'Values')
    is_server = fields.Boolean("For Server Product", default= False)
    sequence = fields.Integer('Sequence', index=True)

    #LIMTED IS_SERVER
    def write(self, vals):                
        if vals.get('is_server'):
            is_exists = self.env['product.digitalpackage'].search([('is_server', '=', True)])
            if is_exists:
                raise UserError("Only one package can be used for the server")
        res = super(ProductDigitalPackage, self).write(vals)
        return res
    
class ProductDigitalPackageValue(models.Model):
    _name = "product.digitalpackage.value" 
    _order = 'sequence, id'
    _description = 'Digital Package Value'

    name = fields.Char(string='Value', required=True, translate=True)
    digital_package_id = fields.Many2one('product.digitalpackage', string="Digital Package", ondelete='cascade', required=True, index=True,)
    # sequence = fields.Integer('Sequence', index=True)
    sequence = fields.Integer('Sequence')
    is_server = fields.Boolean("For Server Product", related="digital_package_id.is_server", store=True)


    


   

    