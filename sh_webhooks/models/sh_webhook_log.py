# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import models, fields, api

class ShWebhookLog(models.Model):
    _name = 'sh.webhook.log'
    _description = 'Webhook Log'
    _order = 'create_date desc'

    direction = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound')
    ], string="Direction", default='outbound', required=True)
    
    webhook_id = fields.Many2one('sh.webhook.action', string="Outbound Webhook", ondelete='cascade')
    incoming_webhook_id = fields.Many2one('sh.webhook.incoming', string="Inbound Webhook", ondelete='cascade')
    
    res_model = fields.Char("Related Model")
    res_id = fields.Integer("Related Record ID")
    
    url = fields.Char("URL")
    method = fields.Char("Method")
    request_header = fields.Text("Request Header")
    request_body = fields.Text("Request Body")
    response_header = fields.Text("Response Header")
    response_body = fields.Text("Response Body")
    status_code = fields.Integer("Status Code")
    state = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error')
    ], string="Status")
    error_msg = fields.Text("Error Message")
    company_id = fields.Many2one('res.company', string='Company')
