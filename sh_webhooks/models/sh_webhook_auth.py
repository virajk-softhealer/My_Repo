# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import models, fields, api

class ShWebhookAuth(models.Model):
    _name = 'sh.webhook.auth'
    _description = 'Webhook Authentication'

    name = fields.Char("Name", required=True)
    auth_type = fields.Selection([
        ('basic', 'Basic Authentication'),
        ('bearer', 'Bearer Token'),
        ('apikey', 'API Key'),
    ], string="Authentication Type", default='basic', required=True)

    # Basic Auth
    username = fields.Char("Username")
    password = fields.Char("Password")

    # Bearer Token
    token = fields.Char("Token")

    # API Key
    api_key_name = fields.Char("API Key Name", default="X-API-Key")
    api_key_value = fields.Char("API Key Value")
    api_key_location = fields.Selection([
        ('header', 'Header'),
        ('query', 'Query String'),
    ], string="API Key Location", default='header')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
