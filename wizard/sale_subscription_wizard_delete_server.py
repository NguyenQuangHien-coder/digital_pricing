# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


# DELETE SERVER
class SaleSubscriptionWizardDeleteServer(models.TransientModel):
    _name = "sale.subscription.wizard.delete.server"
    _description = "Subscription Wizard Delete Server"

    def _default_subscription(self):
        return self.env['sale.subscription'].browse(self._context.get('active_id'))

    @api.model
    def default_get(self, fields):
        default_sub = self.env['sale.subscription'].browse(self._context.get('active_id'))
        res = super(SaleSubscriptionWizardDeleteServer, self).default_get(fields)
        res['subject'] = default_sub.code
        return res

    sale_subscription = fields.Many2one('sale.subscription', string="Subscription", required=True, default=_default_subscription, ondelete="cascade")
    subscription_namespace = fields.Char('Namespace', related='sale_subscription.code')
    # namespace_validate = fields.Char('Enter your NamSpace to complete the action', required=True)
    namespace_validate = fields.Char('You are going to delete the instance ', required=True)
    subject = fields.Char('Subject')
 
           
    def delete_server(self):
        for rec in self:
            if rec.subscription_namespace != rec.namespace_validate:                
                raise UserError(_("Namespace is not correct"))

            rec.sale_subscription.update({
                'hidden_state': 'deleted'
            })    
    

    