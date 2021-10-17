from odoo import fields, models, api


# class ProductTemplateAttributeLine(models.Model):
#     _inherit = "product.template.attribute.line"

#     units = fields.Char('Units')

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    value_number = fields.Integer('Value number')

