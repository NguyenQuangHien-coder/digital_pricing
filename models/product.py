# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"
    _order = 'sequence, id'

    sequence = fields.Integer('sequence', help="Sequence for the handle.", index=True)
    # digital_package_id = fields.Many2one('product.digitalpackage', string="Digital Package", ondelete='cascade', index=True,)
    # digital_package_id = fields.Many2one( string="Digital Package", related="product_tmpl_id.digital_package_id")
    digital_package_value_id = fields.Many2one('product.digitalpackage.value', string="Digital Package Value", ondelete='cascade', index=True, )
    is_server = fields.Boolean("Is Server Product", related="product_tmpl_id.is_value_package", store=True)
    # sale_price = lst_price
    # if custom lst_price: store = True -> error when update config varriant
    sale_price = fields.Float("extra server price", compute='_compute_product_lst_price' ,store = True)

    # inherit
    # lst_price = fields.Float(
    #     'Public Price', compute='_compute_product_lst_price',
    #     digits='Product Price', inverse='_set_product_lst_price',
    #     help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.", store=True )
    
    @api.depends('list_price', 'price_extra')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        to_uom = None
        if 'uom' in self._context:
            to_uom = self.env['uom.uom'].browse(self._context['uom'])

        for product in self:
            if to_uom:
                list_price = product.uom_id._compute_price(product.list_price, to_uom)
            else:
                list_price = product.list_price
            product.lst_price = list_price + product.price_extra
            # CUSTOM CODE
            product.sale_price = product.lst_price
            # END CUSTOM CODE
class ProductCategory(models.Model):
    _inherit = "product.category"

    is_digital_category = fields.Boolean("Digital Category")
    is_checkout_section = fields.Boolean("Checkout Section")
    # checkout_section_name = fields.Char("Checkout Section Name", default="Normal Product")

    # def default_checkout_section_name(self):
    #     for rec in self:
    #         rec.checkout_section_name = 'Normal Product'

    

    



