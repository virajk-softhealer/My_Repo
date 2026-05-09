# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, wrap_module
import requests
import json
import logging
import odoo
import time

_logger = logging.getLogger(__name__)

class ShWebhookAction(models.Model):
    _name = 'sh.webhook.action'
    _description = 'Webhook Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Action Name", required=True, tracking=True)
    model_id = fields.Many2one('ir.model', string="Model", required=True, ondelete='cascade', tracking=True)
    model_name = fields.Char(related='model_id.model', string="Model Name", readonly=True)
    url = fields.Char("Webhook URL", required=True, tracking=True)
    server_action_id = fields.Many2one('ir.actions.server', string="Server Action", ondelete='cascade')
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH')
    ], string="Method", default='POST', required=True)
    timeout = fields.Integer("Timeout", default=25)
    run_type = fields.Selection([
        ('single', 'Single'),
        ('multi', 'Multi')
    ], string="Run Type", default='multi', required=True)
    send_type = fields.Selection([
        ('immediately', 'Immediately'),
        ('post_commit', 'Post Commit'),
        ('cron', 'Cron Job')
    ], string="Send Type", default='immediately', required=True)
    field_ids = fields.Many2many('ir.model.fields', string="Fields")
    
    adapt_url = fields.Boolean("Adapt URL")
    adapt_headers = fields.Boolean("Adapt Headers")
    apply_auth = fields.Boolean("Apply Authentication")
    adapt_payload = fields.Boolean("Adapt Payload")
    process_response = fields.Boolean("Process Response")
    verify_ssl = fields.Boolean("Verify SSL", default=True)
    sudo_fields = fields.Boolean("Sudo Fields")
    
    auth_id = fields.Many2one('sh.webhook.auth', string="Authentication", tracking=True)
    header_ids = fields.One2many('sh.webhook.header', 'webhook_id', string="Header Values")
    
    code_url = fields.Text("URL Code")
    code_headers = fields.Text("Headers Code")
    code_payload = fields.Text("Payload Code")
    code_response = fields.Text("Response Code")
    code_error = fields.Text("Error Code")
    

    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._update_server_action()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['name', 'model_id']):
            for rec in self:
                rec._update_server_action()
        return res

    def _update_server_action(self):
        """ Create or update the linked server action """
        for rec in self:
            action_vals = {
                'name': f"Webhook: {rec.name}",
                'model_id': rec.model_id.id,
                'state': 'code',
                'code': f"model.browse(env.context.get('active_ids', [])).env['sh.webhook.action'].browse({rec.id}).trigger_webhook(records)",
            }
            if rec.server_action_id:
                rec.server_action_id.write(action_vals)
            else:
                rec.server_action_id = self.env['ir.actions.server'].create(action_vals)
            
    def create_contextual_action(self):
        """ Create a contextual action in the model's 'Action' menu """
        for rec in self:
            if rec.server_action_id:
                rec.server_action_id.create_action()

    def remove_contextual_action(self):
        """ Remove the contextual action """
        for rec in self:
            if rec.server_action_id:
                rec.server_action_id.unlink_action()

    def action_preview(self):
        """ Open a wizard to select records for previewing the webhook """
        return {
            'name': _('Select Records to Test'),
            'type': 'ir.actions.act_window',
            'res_model': 'sh.webhook.test.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_webhook_id': self.id, 'default_model_id': self.model_id.id}
        }

    def _get_eval_context(self, records=None):
        """ Prepare evaluation context for Python code """
        return {
            'env': self.env,
            'model': self.env[self.model_name],
            'records': records,
            'record': records[0] if records and len(records) == 1 else None,
            'datetime': fields.Datetime,
            'date': fields.Date,
            'time': wrap_module(time, ['time', 'sleep', 'strftime', 'strptime']),
            'json': wrap_module(json, ['loads', 'dumps', 'JSONEncoder', 'JSONDecoder']),
            'requests': wrap_module(requests, ['get', 'post', 'put', 'patch', 'delete', 'request', 'Response']),
            'log': _logger.info,
            'UserError': ValidationError,
        }

    def _prepare_payload(self, records):
        """ Prepare the payload for the webhook """
        if self.adapt_payload and self.code_payload:
            eval_context = self._get_eval_context(records)
            safe_eval(self.code_payload, eval_context, mode='exec')
            return eval_context.get('payload', {})
        
        payload = []
        for rec in records:
            rec_data = {}
            fields_to_read = self.field_ids.mapped('name') or ['id']
            # Using sudo if configured
            record_to_read = rec.sudo() if self.sudo_fields else rec
            rec_data = record_to_read.read(fields_to_read)[0]
            payload.append(rec_data)
        
        return payload if self.run_type == 'multi' else payload[0]

    def _prepare_headers(self, records):
        """ Prepare the headers for the webhook """
        headers = {header.key: header.value for header in self.header_ids}
        if self.adapt_headers and self.code_headers:
            eval_context = self._get_eval_context(records)
            eval_context['headers'] = headers
            safe_eval(self.code_headers, eval_context, mode='exec')
            headers = eval_context.get('headers', headers)
        return headers

    def _prepare_url(self, records):
        """ Prepare the URL for the webhook """
        url = self.url
        if self.adapt_url and self.code_url:
            eval_context = self._get_eval_context(records)
            eval_context['url'] = url
            safe_eval(self.code_url, eval_context, mode='exec')
            url = eval_context.get('url', url)
        return url

    def trigger_webhook(self, records):
        """ Main method to trigger the webhook call """
        if not records:
            return
        
        if self.send_type == 'immediately':
            self._send_request(records)
        elif self.send_type == 'post_commit':
            # Use post-commit to send after transaction is successful
            self.env.cr.postcommit.add(lambda: self._send_request_with_new_env(records.ids))
        elif self.send_type == 'cron':
            # Placeholder for cron queueing - maybe just a separate log state 'pending'
            # and a cron job to process pending logs.
            # For now, let's just do post_commit as a fallback for cron or implement a queue.
            self.env.cr.postcommit.add(lambda: self._send_request_with_new_env(records.ids))

    def _send_request_with_new_env(self, record_ids):
        """ Send request with a fresh environment (for post-commit) """
       
        new_cr = odoo.registry(self.env.cr.dbname).cursor()
        try:
            with odoo.api.Environment.manage():
                new_env = odoo.api.Environment(new_cr, self.env.uid, self.env.context)
                self.with_env(new_env).browse(self.id)._send_request(new_env[self.model_name].browse(record_ids))
                new_cr.commit()
        finally:
            new_cr.close()

    def _send_request(self, records):
        """ Perform the actual HTTP request """
        url = self._prepare_url(records)
        headers = self._prepare_headers(records)
        payload = self._prepare_payload(records)
        
        try:
            # Apply Authentication
            auth = None
            if self.apply_auth and self.auth_id:
                if self.auth_id.auth_type == 'basic':
                    auth = (self.auth_id.username, self.auth_id.password)
                elif self.auth_id.auth_type == 'bearer':
                    headers['Authorization'] = f"Bearer {self.auth_id.token}"
                elif self.auth_id.auth_type == 'apikey':
                    if self.auth_id.api_key_location == 'header':
                        headers[self.auth_id.api_key_name] = self.auth_id.api_key_value
                    else:
                        if self.method == 'GET':
                            payload[self.auth_id.api_key_name] = self.auth_id.api_key_value
                        else:
                            # Add to URL params if not GET
                            url += ('?' if '?' not in url else '&') + f"{self.auth_id.api_key_name}={self.auth_id.api_key_value}"
        
            # Prepare params/json correctly to avoid ValueError (too many values to unpack)
            is_get = self.method == 'GET'
            request_params = None
            request_json = None
            
            if is_get:
                # GET expects a dictionary or list of tuples. 
                # If we have multiple records, we take the first one or the whole payload if it's already a dict.
                request_params = payload[0] if isinstance(payload, list) and payload else payload
            else:
                request_json = payload

            response = requests.request(
                method=self.method,
                url=url,
                headers=headers,
                auth=auth,
                json=request_json,
                params=request_params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            self._log_request(url, headers, payload, response)
            
            if self.process_response and self.code_response:
                eval_context = self._get_eval_context(records)
                eval_context['response'] = response
                safe_eval(self.code_response, eval_context, mode='exec')
                
        except Exception as e:
            _logger.error("Webhook Error: %s", str(e))
            self._log_request(url, headers, payload, error=e)
            if self.code_error:
                eval_context = self._get_eval_context(records)
                eval_context['error'] = e
                safe_eval(self.code_error, eval_context, mode='exec')

    def _log_request(self, url, headers, payload, response=None, error=None):
        """ Log the webhook attempt """
        log_vals = {
            'webhook_id': self.id,
            'url': url,
            'method': self.method,
            'request_header': json.dumps(headers),
            'request_body': json.dumps(payload),
            'company_id': self.company_id.id,
        }
        if response is not None:
            log_vals.update({
                'response_header': json.dumps(dict(response.headers)),
                'response_body': response.text,
                'status_code': response.status_code,
                'state': 'success' if 200 <= response.status_code < 300 else 'error',
            })
        if error:
            log_vals.update({
                'state': 'error',
                'error_msg': str(error),
            })
        self.env['sh.webhook.log'].sudo().create(log_vals)

class ShWebhookHeader(models.Model):
    _name = 'sh.webhook.header'
    _description = 'Webhook Header'

    webhook_id = fields.Many2one('sh.webhook.action', string="Webhook", required=True, ondelete='cascade')
    key = fields.Char("Key", required=True)
    value = fields.Char("Value", required=True)
