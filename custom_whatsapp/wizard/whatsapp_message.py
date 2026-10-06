# See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.mimetypes import guess_mimetype
import html2text
from odoo.addons.mail.tools.parser import parse_res_ids
from ..wgapi import texttohtml
import base64
import logging
import os
from odoo.tools import config
from datetime import datetime
import json

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
    from phonenumbers.phonenumberutil import region_code_for_country_code
    _sms_phonenumbers_lib_imported = True
except ImportError:
    _sms_phonenumbers_lib_imported = False
    _logger.info(
        "The `phonenumbers` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install phonenumbers` to install it."
    )

class WhatsappComposeMessage(models.TransientModel):
    _name = 'whatsapp.compose.message'
    _description = "Whatsapp Message"

    @api.model
    def default_get(self, fields):
        _logger.info('default_get called with fields: %s and context: %s', fields, self.env.context)
        result = super().default_get(fields)
        context = self.env.context
        if context.get('active_model'):
            _logger.info('Active model: %s', context['active_model'])
            result['model'] = context['active_model']
            if context.get('active_ids') or context.get('active_id'):
                result['res_ids'] = context.get('active_ids') or [context.get('active_id')]
            partners = self.env['res.partner']
            if result['model'] and context['active_model'] and result['model'] == 'res.partner':
                partners = self.env[result['model']].browse(result['res_ids'])
                result['model'] = result['model'] or 'res.partner'
                result['partner_ids'] = [(6, 0, partners.ids)]
            else:
                partners = self.env[result['model']].browse(result['res_ids']).mapped('partner_id')
                result['partner_ids'] = [(6, 0, partners.ids)]
            wa_template_id = self.env['mail.template']._find_default_for_template(result['model'])
            _logger.info('wa_template_id: %s, result.get("wa_template_id"): %s', wa_template_id, result.get('wa_template_id'))
            if wa_template_id and not result.get('wa_template_id'):
                result['template_id'] = wa_template_id.id
            elif not wa_template_id and not result.get('wa_template_id'):
                action = self.env.ref('custom_whatsapp.action_whatsapp_template')
                _logger.warning('No template available for this model, raising RedirectWarning')
                raise RedirectWarning(_("No template available for this model"), action.id, _("View Templates"))
        if context.get('active_ids') and len(context['active_ids']) > 1:
            result['batch_mode'] = True
        _logger.info('default_get result: %s', result)
        return result

    @api.model
    def _get_composition_mode_selection(self):
        return [('comment', 'Post on a document'),
                ('mass_mail', 'Whatsapp Mass Mailing'),
                ('mass_post', 'Post on Multiple Documents')]
        
    composition_mode = fields.Selection(selection=_get_composition_mode_selection, string='Composition mode', default='comment')
    composition_batch = fields.Boolean('Batch composition', compute='_compute_composition_batch')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    subject = fields.Char('Subject')
    message = fields.Text('Contents', compute='_compute_body', readonly=False, store=True)
    batch_mode = fields.Boolean("Is Multiple Records")
    res_domain = fields.Text('Active domain')
    res_id = fields.Integer('Record Document ID', required=False)
    res_ids = fields.Char('Document IDs', required=False)
    model = fields.Char('Object')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'whatsapp_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', string='Attachments')
    location = fields.Boolean('Location')
    partner_address_id = fields.Many2one('res.partner', string='Address')
    lat = fields.Float('Lat')
    long = fields.Float('Long')
    type = fields.Selection([('contact', 'Contacts'),('group', 'Groups')], default='group')
    whatsapp_type = fields.Selection([('post', 'Post'),('get', 'Get')], default='post')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', model), '|', ('user_id','=', False), ('user_id', '=', uid)]"
    )
    send_mode = fields.Selection([
        ('message', 'Message'),
        ('template', 'Template')
    ], string='Send Mode', default='message', required=True, help='Choose to send a custom message or use a template.')
    batch_size = fields.Integer('Batch Size', default=0, help='Number of recipients to process in a batch (for future use or throttling).')

    @api.depends('res_ids')
    def _compute_composition_batch(self):
        for composer in self:
            if composer.res_domain:
                composer.composition_batch = True
                continue
            res_ids = composer._evaluate_res_ids()
            composer.composition_batch = len(res_ids) > 1 if res_ids else False

    def _get_active_records(self):
        self.ensure_one()
        if not self.model or self.model in ('False', 'None', False, None):
            return self.env['res.partner'].browse([])
        if not self.res_ids or self.res_ids in ('False', 'None', False, None):
            return self.env[self.model].browse([])
        try:
            ids = literal_eval(self.res_ids)
            if not isinstance(ids, (list, tuple)):
                ids = [ids]
        except Exception:
            return self.env[self.model].browse([])
        return self.env[self.model].browse(ids)

    @api.model
    def _get_default_mail_body(self, rec, mail_template):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            rec,
            'body_html',
            options={'post_process': True},
        )

    @api.model
    def _get_mail_default_field_value_from_template(self, mail_template, rec, field, **kwargs):
        if not mail_template:
            return
        return mail_template._render_field(field, rec.ids, **kwargs)[rec._origin.id]

    @api.depends('composition_mode', 'model', 'res_ids', 'template_id')
    def _compute_body(self):
        for composer in self:
            rec = composer._get_active_records()
            if composer.template_id and rec:
                # Get the rendered HTML content
                html_content = self._get_default_mail_body(rec, composer.template_id)
                if html_content:
                    # Convert HTML to PDF if it's a template
                    if composer.send_mode == 'template':
                        try:
                            pdf_content = self.env['ir.actions.report'].sudo()._run_wkhtmltopdf(
                                [html_content],
                                specific_paperformat_args={'data-report-margin-top': 10,
                                                        'data-report-margin-bottom': 10}
                            )
                            # Create attachment for the PDF
                            attachment = self.env['ir.attachment'].create({
                                'name': f'template_{composer.template_id.id}.pdf',
                                'type': 'binary',
                                'datas': base64.b64encode(pdf_content),
                                'res_model': 'whatsapp.compose.message',
                                'res_id': composer.id,
                                'mimetype': 'application/pdf'
                            })
                            # Add the PDF to attachments
                            composer.attachment_ids = [(4, attachment.id)]
                            # Set plain text message
                            composer.message = html2text.html2text(html_content)
                        except Exception as e:
                            _logger.error("Error converting template to PDF: %s", str(e))
                            composer.message = html2text.html2text(html_content)
                    else:
                        composer.message = html2text.html2text(html_content)
                else:
                    composer.message = 'Sample Message'
            if not composer.template_id:
                composer.message = False

    @api.depends('composition_mode', 'model', 'res_ids', 'template_id')
    def _compute_attachment_ids(self):
        for composer in self:
            res_ids = composer._evaluate_res_ids() or [0]
            if (composer.template_id.attachment_ids and
                (composer.composition_mode == 'mass_mail' or composer.composition_batch)):
                composer.attachment_ids = composer.template_id.attachment_ids
            elif composer.template_id and composer.composition_mode == 'comment' and len(res_ids) == 1:
                rendered_values = composer._generate_template_for_composer(
                    res_ids,
                    ('attachment_ids', 'attachments'),
                )[res_ids[0]]
                attachment_ids = rendered_values.get('attachment_ids') or []
                if rendered_values.get('attachments'):
                    attachment_ids += self.env['ir.attachment'].create([
                        {'name': attach_fname,
                         'datas': attach_datas,
                         'res_model': 'whatsapp.compose.message',
                         'res_id': 0,
                         'type': 'binary',
                        } for attach_fname, attach_datas in rendered_values.pop('attachments')
                    ]).ids
                if attachment_ids:
                    composer.attachment_ids = attachment_ids
            elif not composer.template_id:
                composer.attachment_ids = False

    def _evaluate_res_ids(self):
        self.ensure_one()
        return parse_res_ids(
            self.env.context.get('composer_force_res_ids') or
            self.res_ids or
            self.env.context.get('active_ids'),
            self.env,
        ) or []

    def _generate_template_for_composer(self, res_ids, render_fields, find_or_create_partners=True):
        self.ensure_one()
        mapping = {
            'attachments': 'report_template_ids',
            'message': 'body_html',
            'partner_ids': 'partner_to',
        }
        template_fields = {mapping.get(fname, fname) for fname in render_fields}
        template_values = self.template_id._generate_template(
            res_ids,
            template_fields,
            find_or_create_partners=True
        )
        exclusion_list = ('email_cc', 'email_to') if find_or_create_partners else ()
        mapping = {'body_html': 'message'}
        render_results = {}
        for res_id in res_ids:
            render_results[res_id] = {
                mapping.get(fname, fname): value
                for fname, value in template_values[res_id].items()
                if fname not in exclusion_list and value
            }
        return render_results

    @api.model
    def generate_email_for_composer(self, template_id, res_ids, fields=None):
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'attachment_ids', 'mail_server_id']
        returned_fields = fields + ['partner_ids', 'attachments']
        values = dict.fromkeys(res_ids, False)
        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id)._generate_template(res_ids, render_fields=fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
            res_id_values['message'] = html2text.html2text(res_id_values.pop('body_html', ''))
            values[res_id] = res_id_values
        return multi_mode and values or values[res_ids[0]]
    
    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        
        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True)\
            .replace(r' ', '\N{NO-BREAK SPACE}').replace(r'-', '-\N{ZERO WIDTH NO-BREAK SPACE}')
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
 
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)
 
    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id
 
    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number
             
    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records    

    def _prepare_mail_message(self, author_id, chat_id, record, model, body, data, subject, partner_ids, attachment_ids, response, status):
        """Prepare values for creating a mail.message record with enhanced error handling"""
        try:
            whatsapp_server = self.env['ir.whatsapp_server'].sudo().search(
                [('status','=','authenticated')], 
                order='sequence asc', 
                limit=1
            )
            
            if not whatsapp_server:
                _logger.error("No authenticated WhatsApp server found while preparing mail message")
                raise UserError(_("No authenticated WhatsApp server found"))

            record_id = record.id if isinstance(record, models.Model) else record
            _logger.debug("Preparing mail message for record ID %s (model: %s)", record_id, model)

            values = {
                'whatsapp_server_id': whatsapp_server.id,
                'author_id': author_id,
                'model': model or 'res.partner',
                'res_id': record_id,
                'body': body,
                'whatsapp_data': data,
                'subject': subject or False,
                'message_type': 'whatsapp',
                'record_name': subject,
                'partner_ids': [(4, pid) for pid in partner_ids],
                'attachment_ids': attachment_ids and [(6, 0, attachment_ids.ids)],
                'whatsapp_method': data.get('method', 'send_message'),
                'whatsapp_chat_id': chat_id,
                'whatsapp_response': json.dumps(response) if isinstance(response, dict) else str(response),
                'whatsapp_status': status,
            }
            _logger.debug("Mail message values prepared successfully")
            return values
        except Exception as e:
            _logger.error("Error preparing mail message: %s", str(e), exc_info=True)
            raise UserError(_("Error preparing message record: %s") % str(e))

    def _save_attachment_to_public(self, attach):
        """Save attachment to public directory with enhanced error handling and logging"""
        try:
            _logger.info("Processing attachment ID %s: %s", attach.id, attach.name)
            
            base_dir = config.get('data_dir')
            if not base_dir:
                _logger.error("data_dir not configured in Odoo config")
                raise UserError(_('Server configuration error: data_dir not set'))
                
            public_dir = os.path.join(base_dir, 'whatsapp_public_docs')
            os.makedirs(public_dir, exist_ok=True)
            _logger.debug("Using public directory: %s", public_dir)
            
            filename = f"{attach.id}_{attach.name.replace('/', '_')}"
            file_path = os.path.join(public_dir, filename)
            _logger.debug("Target file path: %s", file_path)
            
            file_data = attach.datas
            if not file_data and attach.store_fname:
                _logger.debug("Reading from filestore: %s", attach.store_fname)
                file_data = attach._file_read(attach.store_fname)
                if not file_data:
                    raise UserError(_('Empty file data from filestore for %s') % attach.name)
            
            if not file_data:
                raise UserError(_('No data found for attachment %s') % attach.name)
            
            if isinstance(file_data, str):
                file_bytes = base64.b64decode(file_data.strip())
            elif isinstance(file_data, bytes):
                try:
                    file_bytes = base64.b64decode(file_data, validate=True)
                except Exception:
                    file_bytes = file_data
            else:
                raise UserError(_('Invalid file data type for %s') % attach.name)
                
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
                
            try:
                import stat
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except Exception as e:
                _logger.warning("Could not set file permissions: %s", str(e))
            
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if not base_url:
                raise UserError(_('Base URL not configured in system parameters'))
                
            if base_url.endswith('/'):
                base_url = base_url[:-1]
                
            public_url = f"{base_url}/whatsapp_public_docs/{filename}"
            _logger.info("Successfully saved attachment to public URL: %s", public_url)
            return public_url
                
        except Exception as e:
            _logger.error("Error processing attachment %s: %s", attach.name, str(e), exc_info=True)
            raise UserError(_('Failed to process attachment %s: %s') % (attach.name, str(e)))

    def _process_recipient_batch(self, server, client, batch, message, attachments, opt_out_list):
        """Process a batch of recipients with comprehensive error handling"""
        MailMessage = self.env['mail.message']
        failed_recipients = []
        success_count = 0
        
        for partner in batch:
            # Validate WhatsApp number and opt-out before any gateway call
            if not partner.exists():
                _logger.warning("Partner ID %s no longer exists - skipping", partner.id)
                failed_recipients.append(partner.id)
                continue

            whatsapp = partner._formatting_mobile_number()
            _logger.debug("Processing partner %s with WhatsApp number %s", partner.name, whatsapp)

            if not whatsapp or whatsapp == '0' or whatsapp in opt_out_list:
                _logger.info("Skipping partner %s - invalid WhatsApp number or opted out", partner.name)
                failed_recipients.append(partner.id)
                continue

            try:
                # Defensive check before sending to gateway (attachments)
                if not whatsapp or whatsapp == '0' or whatsapp in opt_out_list:
                    _logger.warning("Defensive: Skipping gateway call for partner %s (number: %s)", partner.name, whatsapp)
                    failed_recipients.append(partner.id)
                    continue
                # Process attachments if any
                if attachments:
                    for idx, att in enumerate(attachments):
                        # Defensive check before each attachment send
                        if not whatsapp or whatsapp == '0' or whatsapp in opt_out_list:
                            _logger.warning("Defensive: Skipping gateway call for partner %s (number: %s)", partner.name, whatsapp)
                            failed_recipients.append(partner.id)
                            continue
                        try:
                            # Only set caption for non-PDF attachments or when not in template mode
                            caption = '' if (self.send_mode == 'template' and att['mimetype'] == 'application/pdf') else (message if idx == 0 else '')
                            if att['mimetype'].startswith('image/'):
                                response = client.send_image(
                                    phone=whatsapp,
                                    caption=caption,
                                    image_url=att['url'],
                                    is_group=False
                                )
                                method = 'send_image'
                            else:
                                response = client.send_document(
                                    phone=whatsapp,
                                    caption=caption,
                                    document_url=att['url'],
                                    document_name=att['filename'],
                                    is_group=False
                                )
                                method = 'send_document'

                            # Map status: both 'success' and 'PENDING' are considered successful
                            # Extract status from both top-level and nested 'data'
                            status_val = response.get('status') or response.get('data', {}).get('status')
                            if status_val in ['success', 'PENDING']:
                                status = 'sent'
                            else:
                                status = 'error'
                            _logger.info("Attachment %s sent to %s - Status: %s", att['filename'], whatsapp, status)
                            if status == 'sent':
                                success_count += 1
                        except Exception as e:
                            status = 'error'
                            response = {'error': str(e)}
                            _logger.error("Error sending attachment to %s: %s", whatsapp, str(e), exc_info=True)
                            failed_recipients.append(partner.id)
                            continue

                        # Create message record
                        chat_id = partner.chat_id if partner.chat_id else whatsapp
                        data = {
                            'method': method,
                            'phone': whatsapp,
                            'url': att['url'],
                            'filename': att['filename']
                        }
                        vals = self._prepare_mail_message(
                            self.env.user.partner_id.id,
                            chat_id,
                            partner,
                            'res.partner',
                            texttohtml.formatHtml(caption),
                            data,
                            self.subject,
                            [partner.id],
                            self.attachment_ids,
                            response,
                            'send' if status == 'sent' else 'error'
                        )
                        MailMessage.sudo().create(vals)
                else:
                    # Defensive check before sending text message
                    if not whatsapp or whatsapp == '0' or whatsapp in opt_out_list:
                        _logger.warning("Defensive: Skipping gateway call for partner %s (number: %s)", partner.name, whatsapp)
                        failed_recipients.append(partner.id)
                        continue
                    try:
                        response = client.send_message(
                            phone=whatsapp,
                            message=message,
                            is_group=False
                        )
                        # Check for gateway error (plain error dict)
                        if isinstance(response, dict) and response.get('status') == 'error':
                            _logger.warning("Gateway error for partner %s: %s", partner.name, response.get('message'))
                            failed_recipients.append(partner.id)
                            status = 'error'
                        else:
                            # Extract status from both top-level and nested 'data'
                            status_val = response.get('status') or response.get('data', {}).get('status')
                            if status_val in ['success', 'PENDING']:
                                status = 'send'
                                success_count += 1
                            else:
                                status = 'error'
                                failed_recipients.append(partner.id)
                        _logger.info("Message sent to %s - Status: %s", whatsapp, status)
                    except Exception as e:
                        response = {'error': str(e)}
                        status = 'error'
                        _logger.error("Error sending message to %s: %s", whatsapp, str(e), exc_info=True)
                        failed_recipients.append(partner.id)
                        continue

                    # Always mark as failed if status is error
                    if status == 'error' and partner.id not in failed_recipients:
                        failed_recipients.append(partner.id)

                    # Create message record
                    chat_id = partner.chat_id if partner.chat_id else whatsapp
                    vals = self._prepare_mail_message(
                        self.env.user.partner_id.id,
                        chat_id,
                        partner,
                        'res.partner',
                        texttohtml.formatHtml(message),
                        response,
                        self.subject,
                        [partner.id],
                        [],
                        response,
                        status
                    )
                    MailMessage.sudo().create(vals)

            except Exception as e:
                _logger.error("Unexpected error processing partner %s: %s", partner.id, str(e), exc_info=True)
                failed_recipients.append(partner.id)
                continue

        return {
            'success_count': success_count,
            'failed_recipients': failed_recipients
        }

    def whatsapp_message_post(self):
        """Main method to handle WhatsApp message sending with queue support"""
        _logger.info("WhatsApp message post initiated by user %s", self.env.user.id)
        
        try:
            # Verify WhatsApp server connection
            whatsapp_server = self.env['ir.whatsapp_server'].search(
                [('connection_status', '=', 'connected')], 
                limit=1
            )
            
            if not whatsapp_server:
                _logger.error("No connected WhatsApp server found")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('WhatsApp Send Error'),
                        'message': _('No connected WhatsApp server found. Please check your WhatsApp configuration.'),
                        'type': 'danger',
                        'sticky': True,
                    }
                }

            client = whatsapp_server._get_wgapi_client()
            _logger.info("Using WhatsApp server: %s (ID: %s)", whatsapp_server.name, whatsapp_server.id)

            # Prepare message content and handle template conversion
            if self.send_mode == 'template' and self.template_id:
                # Get active record for template rendering
                rec = self._get_active_records()
                if not rec:
                    raise UserError(_("No record found for template rendering."))
                
                # Render the template with record data
                html_content = self._get_default_mail_body(rec, self.template_id)
                if not html_content:
                    raise UserError(_("Failed to render template content."))
                    
                _logger.debug("Using template: %s with rendered content", self.template_id.name)
                
                try:
                    # Convert template HTML to PDF
                    pdf_content = self.env['ir.actions.report'].sudo()._run_wkhtmltopdf(
                        [html_content],
                        specific_paperformat_args={'data-report-margin-top': 10,
                                                'data-report-margin-bottom': 10}
                    )
                    
                    # Create PDF attachment
                    attachment = self.env['ir.attachment'].create({
                        'name': f'template_{self.template_id.name}.pdf',
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': self._name,
                        'res_id': self.id,
                        'mimetype': 'application/pdf'
                    })
                    
                    # Add to attachment list
                    self.attachment_ids = [(4, attachment.id)]
                    message = self.template_id.subject or 'Document Attached'
                    _logger.debug("Template converted to PDF attachment")
                    
                except Exception as e:
                    _logger.error("Failed to convert template to PDF: %s", str(e))
                    message = html2text.html2text(html_content)
            else:
                message = self.message or ''
                _logger.debug("Using custom message")
            
            message = message.replace("'", '')
            _logger.debug("Message content prepared")

            # # Process attachments
            # attachment_list = []
            # for attach in self.attachment_ids:
            #     try:
            #         public_url = self._save_attachment_to_public(attach)
            #         mimetype = guess_mimetype(base64.b64decode(attach.datas)) if attach.datas else 'application/octet-stream'
            #         attachment_list.append({
            #             'filename': attach.name,
            #             'url': public_url,
            #             'mimetype': mimetype
            #         })
            #         _logger.info("Processed attachment: %s", attach.name)
            #     except Exception as e:
            #         _logger.error("Failed to process attachment %s: %s", attach.name, str(e), exc_info=True)
            #         continue

            # Only process each attachment ONCE and reuse for all recipients
            attachment_list = []
            processed_attachments = set()
            for attach in self.attachment_ids:
                if attach.id in processed_attachments:
                    continue
                try:
                    _logger.info("Processing attachment ID %s: %s", attach.id, attach.name)
                    public_url = self._save_attachment_to_public(attach)
                    _logger.info("Successfully saved attachment to public URL: %s", public_url)
                    mimetype = guess_mimetype(base64.b64decode(attach.datas)) if attach.datas else 'application/octet-stream'
                    attachment_list.append({
                        'filename': attach.name,
                        'url': public_url,
                        'mimetype': mimetype
                    })
                    processed_attachments.add(attach.id)
                    _logger.info("Processed attachment: %s", attach.name)
                except Exception as e:
                    _logger.error("Failed to process attachment %s: %s", attach.name, str(e), exc_info=True)
                    continue

            # Get recipients
            recipients = self.partner_ids
            # If in 'get' mode and no recipients selected, fetch all contacts or groups
            if not recipients and self.whatsapp_type == 'get':
                if self.type == 'contact':
                    recipients = self.env['res.partner'].search([('active', '=', True)])
                elif self.type == 'group':
                    recipients = self.env['res.partner'].search([('category_id', '!=', False)])
                _logger.info("Fetched %d recipients for whatsapp_type 'get' and type '%s'", len(recipients), self.type)
            if not recipients:
                _logger.warning("No valid recipients found")
                raise UserError(_("No valid recipients found for sending messages"))
            
            _logger.info("Preparing to send to %d recipients", len(recipients))

            # Get opt-out list from context
            opt_out_list = self.env.context.get('mass_whatsapp_opt_out_list') or {}
            _logger.debug("Opt-out list contains %d numbers", len(opt_out_list))

            # Process in batches
            batch_size = self.batch_size or 10
            total_recipients = len(recipients)
            total_success = 0
            total_failures = []
            
            _logger.info("Starting batch processing with batch size %d", batch_size)
            
            for i in range(0, total_recipients, batch_size):
                batch = recipients[i:i + batch_size]
                _logger.info("Processing batch %d-%d of %d", i+1, min(i+batch_size, total_recipients), total_recipients)
                try:
                    batch_result = self._process_recipient_batch(
                        whatsapp_server,
                        client,
                        batch,
                        message,
                        attachment_list,
                        opt_out_list
                    )
                    total_success += batch_result['success_count']
                    total_failures.extend(batch_result['failed_recipients'])
                    _logger.info("Batch %d-%d completed: %d success, %d failures",
                               i+1, i+batch_size,
                               batch_result['success_count'],
                               len(batch_result['failed_recipients']))
                except UserError as ue:
                    _logger.error("UserError in batch %d-%d: %s", i+1, i+batch_size, str(ue))
                    # Only log, do not raise to user
                    continue
                except Exception as e:
                    _logger.error("Error processing batch %d-%d: %s", i+1, i+batch_size, str(e), exc_info=True)
                    # Only log, do not raise to user
                    continue

            # Final status report
            _logger.info("Message sending completed: %d successful, %d failed", total_success, len(total_failures))
            notif_type = 'success' if len(total_failures) == 0 else 'warning'
            notif_msg = _('WhatsApp sending complete: %d successful, %d failed.') % (total_success, len(total_failures))
            if total_failures:
                failed_names = self.env['res.partner'].browse(total_failures).mapped('name')
                if failed_names:
                    notif_msg += '\n' + _('Failed: ') + ', '.join(failed_names)
            # Display notification to user only (let user close the wizard manually)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Send Result'),
                    'message': notif_msg,
                    'type': notif_type,
                    'sticky': notif_type == 'danger',
                }
            }
        #Close the window (no notification)

            # return {'type': 'ir.actions.act_window_close'}
        except Exception as e:
            _logger.error("WhatsApp message sending failed: %s", str(e), exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Send Error'),
                    'message': _('WhatsApp message sending failed: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
