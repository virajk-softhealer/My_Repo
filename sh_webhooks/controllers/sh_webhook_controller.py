# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class ShWebhookController(http.Controller):

    @http.route(['/sh_webhooks/incoming/<string:token>'], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def handle_incoming_webhook(self, token, **kwargs):
        """ Handle incoming webhooks (GET, POST, JSON, Form-data) """
        webhook = request.env['sh.webhook.incoming'].sudo().search([('token', '=', token), ('active', '=', True)], limit=1)
        if not webhook:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Invalid token or inactive webhook'}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )
        
        payload = {}
        if request.httprequest.method == 'GET':
            payload = kwargs
        else:
            # Check if it's a JSON payload
            if request.httprequest.content_type == 'application/json':
                try:
                    payload = request.get_json_data()
                except Exception:
                    payload = {}
            else:
                # POST form-data
                payload = request.params
            
        headers = request.httprequest.headers
        
        # Process the request
        result = webhook.process_request(request, payload, headers)
        return request.make_response(json.dumps(result), headers=[('Content-Type', 'application/json')])
