# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval, wrap_module
import uuid
import json
import logging

_logger = logging.getLogger(__name__)

class ShWebhookIncoming(models.Model):
    _name = 'sh.webhook.incoming'
    _description = 'Incoming Webhook Route'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Name", required=True, tracking=True)
    token = fields.Char("Token", required=True, default=lambda self: str(uuid.uuid4()), copy=False)
    active = fields.Boolean(default=True)
    
    model_id = fields.Many2one('ir.model', string="Model", tracking=True)
    model_name = fields.Char(related='model_id.model', string="Model Name", readonly=True)
    
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
    ], string="Method", default='POST', required=True)
    
    code = fields.Text("Python Code", default="""# Available variables:
#  - env: Odoo environment
#  - model: Odoo model (if specified)
#  - request: The Odoo request object
#  - payload: The JSON/Form payload received
#  - headers: The HTTP headers
#  - log: log function
#  - result: dict to return as JSON response

# Example:
# model.create({'name': payload.get('name')})
# result.update({'status': 'ok'})
""", required=True)

    url = fields.Char("Webhook URL", compute='_compute_url', store=False)

    @api.depends('token')
    def _compute_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.url = f"{base_url}/sh_webhooks/incoming/{rec.token}"

    def process_request(self, request_obj, payload, headers):
        """ Process the incoming request using safe_eval """
        self.ensure_one()
        result = {'status': 'success'}
        eval_context = {
            'env': self.env,
            'model': self.env[self.model_name] if self.model_name else None,
            'request': request_obj,
            'payload': payload,
            'headers': headers,
            'datetime': fields.Datetime,
            'date': fields.Date,
            'json': wrap_module(json, ['loads', 'dumps', 'JSONEncoder', 'JSONDecoder']),
            'log': _logger.info,
            'result': result,
        }
        try:
            safe_eval(self.code, eval_context, mode='exec')
            state = 'error' if result.get('status') == 'error' else 'success'
            self._log_request(request_obj, payload, headers, result, state=state)
            return result
        except Exception as e:
            _logger.error("Incoming Webhook Error: %s", str(e))
            self._log_request(request_obj, payload, headers, result, error=e, state='error')
            return {'status': 'error', 'message': str(e)}

    def _log_request(self, request_obj, payload, headers, result, error=None, state='success'):
        log_vals = {
            'direction': 'inbound',
            'incoming_webhook_id': self.id,
            'url': self.url,
            'method': request_obj.httprequest.method,
            'request_header': json.dumps(dict(headers)),
            'request_body': json.dumps(payload),
            'response_body': json.dumps(result),
            'status_code': 200 if state == 'success' else 500,
            'state': state,
            'company_id': self.env.company.id,
        }
        if error:
            log_vals['error_msg'] = str(error)
        self.env['sh.webhook.log'].sudo().create(log_vals)
