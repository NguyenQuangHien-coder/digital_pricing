# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

# DELETE SERVER
class SaleSubscriptionWizardRedeployServer(models.TransientModel):
    _name = "sale.subscription.wizard.redeploy.server"
    _description = "Subscription Wizard Redeploy Server"

    def _default_subscription(self):
        return self.env['sale.subscription'].browse(self._context.get('active_id'))

    sale_subscription = fields.Many2one('sale.subscription', string="Subscription", required=True, default=_default_subscription, ondelete="cascade")
   
    def redeploy_server(self):
        for rec in self:          
            rec.sale_subscription.update({
                'hidden_state': 'running'
            })    
