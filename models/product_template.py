import itertools
import logging
from collections import defaultdict

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    _order = "name"
   
    is_value_package = fields.Boolean('Server Package')

    # related_products = fields.Many2many("product.template", "related_product_rel","product_id","related_product_id", string="Related Products",)
    # selling_description = fields.Char('Selling Description')
    # technical_name = fields.Char('Technical Name')
    # dependencies = fields.Text('Dependencies')
    # software_product = fields.Boolean('Software Product')
   
   #LIMTED VALUE PACKAGE
    def write(self, vals):                
        if vals.get('is_value_package'):
            is_exists = self.env['product.template'].search([('is_value_package', '=', True)])
            if is_exists:
                raise UserError("Action Limited")
        res = super(ProductTemplate, self).write(vals)
        return res

        


            