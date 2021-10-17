# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import float_compare


_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _invoice_sale_orders(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'):
            for trans in self.filtered(lambda t: t.sale_order_ids):
                trans = trans.with_company(trans.acquirer_id.company_id)\
                    .with_context(company_id=trans.acquirer_id.company_id.id)
                trans.sale_order_ids._force_lines_to_invoice_policy_order()
                invoices = trans.sale_order_ids._create_invoices(final=True)
                trans.invoice_ids = [(6, 0, invoices.ids)]