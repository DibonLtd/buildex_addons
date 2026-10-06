# # See LICENSE file for full copyright and licensing details.

# from ast import literal_eval
# from odoo import api, fields, models, sql_db, _, tools, Command
# from odoo.tools.misc import formatLang, get_lang, format_amount
# # from odoo.tools import format_amount
# from odoo.exceptions import ValidationError, RedirectWarning
# from odoo.tools.mimetypes import guess_mimetype
# from datetime import datetime
# from odoo.tools import pycompat
# from odoo.exceptions import UserError
# import html2text
# from odoo.tools import is_html_empty
# from odoo.addons.mail.tools.parser import parse_res_ids
# from ..wgapi import texttohtml
# from odoo.tools.misc import html_escape
# import requests
# import json
# import ast
# import base64
# import threading
# import time
# import logging
# import os
# from odoo.tools import config

# _logger = logging.getLogger(__name__)


# try:
#     import phonenumbers
#     from phonenumbers.phonenumberutil import region_code_for_country_code
#     _sms_phonenumbers_lib_imported = True

# except ImportError:
#     _sms_phonenumbers_lib_imported = False
#     _logger.info(
#         "The `phonenumbers` Python module is not available. "
#         "Phone number validation will be skipped. "
#         "Try `pip3 install phonenumbers` to install it."
#     )
    

# # def _reopen(self, res_id, model, context=None):
# #     # save original model in context, because selecting the list of available
# #     # templates requires a model in context
# #     context = dict(context or {}, default_model=model)
# #     action = {'type': 'ir.actions.act_window',
# #             'view_mode': 'form',
# #             'res_id': res_id,
# #             'res_model': self._name,
# #             'target': 'new',
# #             'context': context,
# #             }
# #     print ('===action==',action)
# #     return action

# class WhatsappComposeMessage(models.TransientModel):
#     _name = 'whatsapp.compose.message'
#     _description = "Whatsapp Message"

#     @api.model
#     def default_get(self, fields):
#         _logger.info('default_get called with fields: %s and context: %s', fields, self.env.context)
#         result = super().default_get(fields)
#         context = self.env.context
#         if context.get('active_model'):
#             _logger.info('Active model: %s', context['active_model'])
#             result['model'] = context['active_model']
#             if context.get('active_ids') or context.get('active_id'):
#                 result['res_ids'] = context.get('active_ids') or [context.get('active_id')]
#             partners = self.env['res.partner']
#             if result['model'] and context['active_model'] and result['model'] == 'res.partner':
#                 partners = self.env[result['model']].browse(result['res_ids'])
#                 result['model'] = result['model'] or 'res.partner'
#                 result['partner_ids'] = [(6, 0, partners.ids)]
#             else:
#                 partners = self.env[result['model']].browse(result['res_ids']).mapped('partner_id')
#                 result['partner_ids'] = [(6, 0, partners.ids)]
#             wa_template_id = self.env['mail.template']._find_default_for_template(result['model'])
#             _logger.info('wa_template_id: %s, result.get("wa_template_id"): %s', wa_template_id, result.get('wa_template_id'))
#             if wa_template_id and not result.get('wa_template_id'):
#                 result['template_id'] = wa_template_id.id
#             elif not wa_template_id and not result.get('wa_template_id'):
#                 action = self.env.ref('custom_whatsapp.action_whatsapp_template')
#                 _logger.warning('No template available for this model, raising RedirectWarning')
#                 raise RedirectWarning(_("No template available for this model"), action.id, _("View Templates"))
#         if context.get('active_ids') and len(context['active_ids']) > 1:
#             result['batch_mode'] = True
#         _logger.info('default_get result: %s', result)
#         return result

#     @api.model
#     def _get_composition_mode_selection(self):
#         return [('comment', 'Post on a document'),
#                 ('mass_mail', 'Whatsapp Mass Mailing'),
#                 ('mass_post', 'Post on Multiple Documents')]
        
#     #invoice_ids = fields.Many2many('account.invoice', string='Invoice')
#     composition_mode = fields.Selection(selection=_get_composition_mode_selection, string='Composition mode', default='comment')
#     composition_batch = fields.Boolean(
#         'Batch composition', compute='_compute_composition_batch')  # more than 1 record (raw source)
#     partner_ids = fields.Many2many('res.partner', string='Contacts')
#     subject = fields.Char('Subject')
#     # message = fields.Text()
#     message = fields.Text(
#         'Contents',
#         # render_engine='qweb', render_options={'post_process': True},
#         # sanitize_style=True,
#         compute='_compute_body', readonly=False, store=True)
#     batch_mode = fields.Boolean("Is Multiple Records")
#     #message_html = fields.Html()
#     res_domain = fields.Text('Active domain')
#     res_id = fields.Integer('Record Document ID', required=False)
#     res_ids = fields.Char('Document IDs', required=False)
#     model = fields.Char('Object')
#     attachment_ids = fields.Many2many(
#         'ir.attachment', 'whatsapp_compose_message_ir_attachments_rel',
#         'wizard_id', 'attachment_id', string='Attachments')
#     #url_link = fields.Char('Url')
#     location = fields.Boolean('Location')
#     partner_address_id = fields.Many2one('res.partner', string='Address')
#     lat = fields.Float('Lat')
#     long = fields.Float('Long')
#     type = fields.Selection([('contact', 'Contacts'),('group', 'Groups')], default='group')
#     whatsapp_type = fields.Selection([('post', 'Post'),('get', 'Get')], default='post')
#     template_id = fields.Many2one(
#         'mail.template', 'Use template', index=True,
#         domain="[('model', '=', model), '|', ('user_id','=', False), ('user_id', '=', uid)]"
#         )
#     send_mode = fields.Selection([
#         ('message', 'Message'),
#         ('template', 'Template')
#     ], string='Send Mode', default='message', required=True, help='Choose to send a custom message or use a template.')

#     @api.depends('res_ids')
#     def _compute_composition_batch(self):
#         """ Determine if batch mode is activated:

#           * using res_domain: always batch (even if result is singleton at a
#             given time, it is user and time dependent, hence batch);
#           * res_ids: if more than one item in the list (void and singleton are
#             not batch);
#         """
#         for composer in self:
#             if composer.res_domain:
#                 composer.composition_batch = True
#                 continue
#             res_ids = composer._evaluate_res_ids()
#             composer.composition_batch = len(res_ids) > 1 if res_ids else False

#     # @api.onchange('template_id')
#     # def _onchange_template_id_wrapper(self):
#     #     self.ensure_one()
#     #     # records = self._get_active_records()
#     #     # res_id = self._context.get('active_id') or 1
#     #     print ('==_onchange_template_id_wrapper==',self.template_id.id, self.composition_mode, self.model, self.res_id, self.res_ids)
#     #     if self.res_ids:
#     #         res_id = ast.literal_eval(self.res_ids)[0]
#     #         values = self._onchange_template_id(self.template_id.id, self.composition_mode, self.model, res_id)['value']
#     #         for fname, value in values.items():
#     #             setattr(self, fname, value)

    
#     # def _onchange_template_id(self, template_id, composition_mode, model, res_id):
#     #     """ - mass_mailing: we cannot render, so return the template values
#     #         - normal mode: return rendered values
#     #         /!\ for x2many field, this onchange return command instead of ids
#     #     """
#     #     if template_id and composition_mode == 'mass_mail':
#     #         template = self.env['mail.template'].browse(template_id)
#     #         values = dict(
#     #             (field, template[field])
#     #             for field in ['subject', 'body_html',
#     #                         #   'email_from',
#     #                           'reply_to',
#     #                           'mail_server_id']
#     #             if template[field]
#     #         )
#     #         if template.sudo().attachment_ids:
#     #             values['attachment_ids'] = [att.id for att in template.sudo().attachment_ids]
#     #         if template.mail_server_id:
#     #             values['mail_server_id'] = template.mail_server_id.id
#     #     elif template_id:
#     #         values = self.generate_email_for_composer(
#     #             template_id, [res_id],
#     #             ['subject', 'body_html',
#     #             #  'email_from',
#     #              'email_cc', 'email_to', 'partner_to', 'reply_to',
#     #              'attachment_ids', 'report_template_ids', 'mail_server_id'
#     #             ]
#     #         )[res_id]
#     #         # transform attachments into attachment_ids; not attached to the document because this will
#     #         # be done further in the posting process, allowing to clean database if email not send
#     #         attachment_ids = []
#     #         Attachment = self.env['ir.attachment'].sudo()
#     #         for attach_fname, attach_datas in values.pop('attachments', []):
#     #             data_attach = {
#     #                 'name': attach_fname,
#     #                 'datas': attach_datas,
#     #                 'res_model': 'whatsapp.compose.message',
#     #                 'res_id': res_id,
#     #                 'type': 'binary',  # override default_type from context, possibly meant for another model!
#     #             }
#     #             print ('==attach_fname==',attach_fname,res_id)
#     #             attachment_ids.append(Attachment.create(data_attach).id)
#     #         if values.get('attachment_ids', []) or attachment_ids:
#     #             values['attachment_ids'] = [Command.set(values.get('attachment_ids', []) + attachment_ids)]
#     #     else:
#     #         default_values = self.with_context(
#     #             default_composition_mode=composition_mode,
#     #             default_model=model,
#     #             default_res_id=res_id
#     #         ).default_get(['composition_mode', 'model', 'res_id', 'parent_id',
#     #                        'subject', 'body',
#     #                     #    'email_from',
#     #                        'partner_ids', 'reply_to',
#     #                        'attachment_ids', 'mail_server_id'
#     #                       ])
#     #         values = dict(
#     #             (key, default_values[key])
#     #             for key in ['subject', 'body',
#     #                         # 'email_from',
#     #                         'partner_ids', 'reply_to',
#     #                         'attachment_ids', 'mail_server_id'
#     #                        ] if key in default_values)

#     #     if values.get('body_html'):
#     #         values['body'] = values.pop('body_html')

#     #     # This onchange should return command instead of ids for x2many field.
#     #     values = self.sudo()._convert_to_write(values)

#     #     return {'value': values}
    

#     def _get_active_records(self):
#         self.ensure_one()
#         # Fix: handle empty or invalid res_ids and model gracefully
#         if not self.model or self.model in ('False', 'None', False, None):
#             return self.env['res.partner'].browse([])  # fallback to a valid model, or use []
#         if not self.res_ids or self.res_ids in ('False', 'None', False, None):
#             return self.env[self.model].browse([])
#         try:
#             ids = literal_eval(self.res_ids)
#             if not isinstance(ids, (list, tuple)):
#                 ids = [ids]
#         except Exception:
#             return self.env[self.model].browse([])
#         return self.env[self.model].browse(ids)

#     @api.model
#     def _get_default_mail_body(self, rec, mail_template):
#         return self._get_mail_default_field_value_from_template(
#             mail_template,
#             rec,
#             'body_html',
#             options={'post_process': True},
#         )

#     @api.model
#     def _get_mail_default_field_value_from_template(self, mail_template, rec, field, **kwargs):
#         if not mail_template:
#             return
#         return mail_template\
#             ._render_field(field, rec.ids, **kwargs)[rec._origin.id]

#     @api.depends('composition_mode', 'model', 'res_ids',
#                  'template_id')
#     def _compute_body(self):
#         """ Computation is coming either from template, either reset. When
#         having a template with a value set, copy it (in batch mode) or render
#         it (in monorecord comment mode) on the composer. When removing the
#         template, reset it. """
#         for composer in self:
#             rec = composer._get_active_records()
#             if composer.template_id and rec:
#                 # composer.message = self._get_html_preview_whatsapp(rec=rec)
#                 composer.message = html2text.html2text(self._get_default_mail_body(rec, composer.template_id)) if self.template_id.body_html else 'Sample Message'
#                 # composer.message = html2text.html2text(self.template_id.body_html) if self.template_id.body_html else 'Sample Message'
#                 # composer._set_value_from_template('body_html', 'message')
#             if not composer.template_id:
#                 composer.message = False

#     @api.depends('composition_mode', 'model', 'res_ids', 'template_id')
#     def _compute_attachment_ids(self):
#         """ Computation is based on template and composition mode. In monorecord
#         comment mode, template is used to generate attachments based on both
#         attachment_ids of template, and reports coming from report_template_ids.
#         Those are generated based on the current record to display. As template
#         generation returns a list of tuples, new attachments are created on
#         the fly during the compute.

#         In batch or email mode, only attachment_ids from template are used on
#         the composer. Reports will be generated at sending time.

#         When template is removed, attachments are reset. """
#         for composer in self:
#             res_ids = composer._evaluate_res_ids() or [0]
#             if (composer.template_id.attachment_ids and
#                 (composer.composition_mode == 'mass_mail' or composer.composition_batch)):
#                 composer.attachment_ids = composer.template_id.attachment_ids
#             elif composer.template_id and composer.composition_mode == 'comment' and len(res_ids) == 1:
#                 rendered_values = composer._generate_template_for_composer(
#                     res_ids,
#                     ('attachment_ids', 'attachments'),
#                 )[res_ids[0]]
#                 attachment_ids = rendered_values.get('attachment_ids') or []
#                 # transform attachments into attachment_ids; not attached to the
#                 # document because this will be done further in the posting
#                 # process, allowing to clean database if email not send
#                 if rendered_values.get('attachments'):
#                     attachment_ids += self.env['ir.attachment'].create([
#                         {'name': attach_fname,
#                          'datas': attach_datas,
#                          'res_model': 'whatsapp.compose.message',
#                          'res_id': 0,
#                          'type': 'binary',    # override default_type from context, possibly meant for another model!
#                         } for attach_fname, attach_datas in rendered_values.pop('attachments')
#                     ]).ids
#                 if attachment_ids:
#                     composer.attachment_ids = attachment_ids
#             elif not composer.template_id:
#                 composer.attachment_ids = False

#     def _evaluate_res_ids(self):
#         """ Parse composer res_ids, which can be: an already valid list or
#         tuple (generally in code), a list or tuple as a string (coming from
#         actions). Void strings / missing values are evaluated as an empty list.

#         Note that 'active_ids' context key is supported at this point as mailing
#         on big ID list would create issues if stored in database.

#         Another context key 'composer_force_res_ids' is temporarily supported
#         to ease support of accounting wizard, while waiting to implement a
#         proper solution to language management.

#         :return: a list of IDs (empty list in case of falsy strings)"""
#         self.ensure_one()
#         return parse_res_ids(
#             self.env.context.get('composer_force_res_ids') or
#             self.res_ids or
#             self.env.context.get('active_ids'),
#             self.env,
#         ) or []

#     # def _set_value_from_template(self, template_fname, composer_fname=False):
#     #     """ Set composer value from its template counterpart. In monorecord
#     #     comment mode, we get directly the rendered value, giving the real
#     #     value to the user. Otherwise we get the raw (unrendered) value from
#     #     template, as it will be rendered at send time (for mass mail, whatever
#     #     the number of contextual records to mail) or before posting on records
#     #     (for comment in batch).

#     #     :param str template_fname: name of field on template model, used to
#     #       fetch the value (and maybe render it);
#     #     :param str composer_fname: name of field on composer model, when field
#     #       names do not match (e.g. body_html on template used to populate body
#     #       on composer);
#     #     """
#     #     self.ensure_one()
#     #     composer_fname = composer_fname or template_fname

#     #     # fetch template value, check if void
#     #     template_value = self.template_id[template_fname] if self.template_id else False
#     #     if template_value and template_fname == 'body_html':
#     #         template_value = template_value if not is_html_empty(template_value) else False
#     #         template_value = html2text.html2text(template_value)
#     #     if template_value:
#     #         if self.composition_mode == 'comment' and not self.composition_batch:
#     #             res_ids = self._evaluate_res_ids()
#     #             rendering_res_ids = res_ids or [0]
#     #             self[composer_fname] = self.template_id._generate_template(
#     #                 rendering_res_ids,
#     #                 {template_fname},
#     #             )[rendering_res_ids[0]][template_fname]
#     #         else:
#     #             self[composer_fname] = self.template_id[template_fname]
#     #     # html2text.html2text(res_id_values.pop('body_html', ''))
#     #     print ('==compose==',html2text.html2text(self[composer_fname]),)
#     #     return html2text.html2text(self[composer_fname])

#     def _generate_template_for_composer(self, res_ids, render_fields,
#                                         find_or_create_partners=True):
#         """ Generate values based on template and relevant values for the
#         mail.compose.message wizard.

#         :param list res_ids: list of record IDs on which template is rendered;
#         :param list render_fields: list of fields to render on template;
#         :param boolean find_or_create_partners: transform emails into partners
#           (see ``Template._generate_template_recipients``);

#         :returns: a dict containing all asked fields for each record ID given by
#           res_ids. Note that

#           * 'body' comes from template 'body_html' generation;
#           * 'attachments' is an additional key coming with 'attachment_ids' due
#             to report generation (in the format [(report_name, data)] where data
#             is base64 encoded);
#           * 'partner_ids' is returned due to recipients generation that gives
#             partner ids coming from default computation as well as from email
#             to partner convert (see ``find_or_create_partners``);
#         """
#         self.ensure_one()

#         # some fields behave / are named differently on template model
#         mapping = {
#             'attachments': 'report_template_ids',
#             'message': 'body_html',
#             'partner_ids': 'partner_to',
#         }
#         template_fields = {mapping.get(fname, fname) for fname in render_fields}
#         template_values = self.template_id._generate_template(
#             res_ids,
#             template_fields,
#             find_or_create_partners=True
#         )
#         # res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
#         # res_id_values['message'] = html2text.html2text(res_id_values.pop('body_html', ''))
#         exclusion_list = ('email_cc', 'email_to') if find_or_create_partners else ()
#         mapping = {'body_html': 'message'}
#         render_results = {}
#         for res_id in res_ids:
#             render_results[res_id] = {
#                 mapping.get(fname, fname): value
#                 for fname, value in template_values[res_id].items()
#                 if fname not in exclusion_list and value
#             }
#             # print ('===s==',render_results[res_id])
#         return render_results

#     # def action_save_as_template(self):
#     #     """ hit save as template button: current form value will be a new
#     #         template attached to the current document. """
#     #     for record in self:
#     #         model = self.env['ir.model']._get(record.model or 'mail.message')
#     #         model_name = model.name or ''
#     #         template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
#     #         values = {
#     #             'name': template_name,
#     #             'subject': record.subject or False,
#     #             'body_html': record.body or False,
#     #             'model_id': model.id or False,
#     #             'use_default_to': True,
#     #         }
#     #         template = self.env['mail.template'].create(values)

#     #         if record.attachment_ids:
#     #             attachments = self.env['ir.attachment'].sudo().browse(record.attachment_ids.ids).filtered(
#     #                 lambda a: a.res_model == 'mail.compose.message' and a.create_uid.id == self._uid)
#     #             if attachments:
#     #                 attachments.write({'res_model': template._name, 'res_id': template.id})
#     #             template.attachment_ids |= record.attachment_ids

#     #         # generate the saved template
#     #         record.write({'template_id': template.id})
#     #         record._onchange_template_id_wrapper()
#     #         return _reopen(self, record.id, record.model, context=self._context)
    
#     # @api.onchange('template_id')
#     # def onchange_template_id_wrapper(self):
#     #     self.ensure_one()
#     #     res_id = self._context.get('active_id') or 1
#     #     values = self.onchange_template_id(self.template_id.id, self.model, res_id)['value']
#     #     for fname, value in values.items():
#     #         setattr(self, fname, value)
    
#     # def onchange_template_id(self, template_id, model, res_id):
#     #     """ - mass_mailing: we cannot render, so return the template values
#     #         - normal mode: return rendered values
#     #         /!\ for x2many field, this onchange return command instead of ids
#     #     """
#     #     if template_id:
#     #         values = self.generate_email_for_composer(template_id, [res_id])[res_id]
#     #     else:
#     #         default_values = self.with_context(default_model=model, default_res_id=res_id).default_get(['model', 'res_id', 'partner_ids', 'message', 'attachment_ids'])
#     #         values = dict((key, default_values[key]) for key in ['subject', 'body', 'partner_ids', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'] if key in default_values)
#     #     # This onchange should return command instead of ids for x2many field.
#     #     # ORM handle the assignation of command list on new onchange (api.v8),
#     #     # this force the complete replacement of x2many field with
#     #     # command and is compatible with onchange api.v7
#     #     values = self._convert_to_write(values)
#     #     return {'value': values}
    
#     # @api.model
#     # def generate_email_for_composer(self, template_id, res_ids, fields=None):
#     #     """ Call email_template.generate_email(), get fields relevant for
#     #         mail.compose.message, transform email_cc and email_to into partner_ids """
#     #     multi_mode = True
#     #     if isinstance(res_ids, pycompat.integer_types):
#     #         multi_mode = False
#     #         res_ids = [res_ids]

#     #     if fields is None:
#     #         fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
#     #     returned_fields = fields + ['partner_ids', 'attachments']
#     #     values = dict.fromkeys(res_ids, False)
#     #     print ('===res_ids==',values)
#     #     template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id).generate_email(res_ids, fields=fields)
#     #     for res_id in res_ids:
#     #         res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
#     #         res_id_values['message'] = html2text.html2text(res_id_values.pop('body_html', ''))
#     #         values[res_id] = res_id_values

#     #     return multi_mode and values or values[res_ids[0]]
    
#     @api.model
#     def generate_email_for_composer(self, template_id, res_ids, fields=None):
#         """ Call email_template.generate_email(), get fields relevant for
#             whatsapp.compose.message, transform email_cc and email_to into partner_ids """
#         multi_mode = True
#         if isinstance(res_ids, int):
#             multi_mode = False
#             res_ids = [res_ids]

#         if fields is None:
#             fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
#         returned_fields = fields + ['partner_ids', 'attachments']
#         values = dict.fromkeys(res_ids, False)
#         # print ('==template_values=11=',fields)
#         template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id)._generate_template(res_ids, render_fields=fields)
#         # print ('==template_values==',template_values)
#         for res_id in res_ids:
#             res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
#             res_id_values['message'] = html2text.html2text(res_id_values.pop('body_html', ''))
#             values[res_id] = res_id_values
#         # print ('==template_values=22=',fields)
#         return multi_mode and values or values[res_ids[0]]
    
#     def format_amount(self, amount, currency):
#         fmt = "%.{0}f".format(currency.decimal_places)
#         lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        
#         formatted_amount = lang.format(fmt, currency.round(amount), grouping=True)\
#             .replace(r' ', '\N{NO-BREAK SPACE}').replace(r'-', '-\N{ZERO WIDTH NO-BREAK SPACE}')
#         pre = post = u''
#         if currency.position == 'before':
#             pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
#         else:
#             post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
 
#         return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)
 
#     def _phone_get_country(self, partner):
#         if 'country_id' in partner:
#             return partner.country_id
#         return self.env.user.company_id.country_id
 
#     def _msg_sanitization(self, partner, field_name):
#         number = partner[field_name]
#         if number and _sms_phonenumbers_lib_imported:
#             country = self._phone_get_country(partner)
#             country_code = country.code if country else None
#             try:
#                 phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
#             except phonenumbers.phonenumberutil.NumberParseException:
#                 return number
#             if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
#                 return number
#             phone_fmt = phonenumbers.PhoneNumberFormat.E164
#             return phonenumbers.format_number(phone_nbr, phone_fmt)
#         else:
#             return number
             
#     def _get_records(self, model):
#         if self.env.context.get('active_domain'):
#             records = model.search(self.env.context.get('active_domain'))
#         elif self.env.context.get('active_ids'):
#             records = model.browse(self.env.context.get('active_ids', []))
#         else:
#             records = model.browse(self.env.context.get('active_id', []))
#         return records    


#     # @api.model
#     # def default_get(self, fields):
#     #     result = super(WhatsappComposeMessage, self).default_get(fields)
#     #     context = dict(self._context or {})
#     #     Attachment = self.env['ir.attachment']
#     #     active_model = context.get('active_model')
#     #     active_ids = context.get('active_ids')
#     #     active_id = context.get('active_id')
#     #     msg = result.get('message', '')
#     #     result['message'] = msg
#     #     #=======================================================================
#     #     # UPDATE PATCH
#     #     #=======================================================================
#     #     WhatsappServer = self.env['ir.whatsapp_server']
#     #     whatsapp_id = WhatsappServer.search([('status','=','authenticated')], order='sequence asc', limit=1)
#     #     if active_ids and whatsapp_id and ast.literal_eval(str(whatsapp_id.message_response)) and len(active_ids) > ast.literal_eval(str(whatsapp_id.message_response))['block_limit']:
#     #         raise UserError(_('Maximum blast message whatsapp is %s.') % str(ast.literal_eval(str(whatsapp_id.message_response))['block_limit']))
#     #     #=======================================================================
#     #     #result['model'] = active_model
#     #     #print ('--active_model--',rec)
#     #     partners = self.env['res.partner']
#     #     if active_model and active_ids and active_model == 'res.partner':
#     #         partners = self.env[active_model].browse(active_ids)
#     #         result['model'] = active_model or 'res.partner'
#     #         result['partner_ids'] = [(6, 0, partners.ids)]
#     #     if active_model and active_ids and active_model != 'res.partner':
#     #         active = self.env[active_model].browse(active_id)
#     #         if active_model == 'sale.order.line':                
#     #             if active.order_partner_id:
#     #                 partners = active.order_partner_id
#     #                 if active.order_partner_id.child_ids:
#     #                     for partner in active.order_partner_id.child_ids:
#     #                         partners += partner.id
#     #         else:
#     #             if active.partner_id:
#     #                 partners = active.partner_id
#     #                 if active.partner_id.child_ids:
#     #                     for partner in active.partner_id.child_ids:
#     #                         partners += partner
#     #         if not partners:
#     #             partners = self.env.user.partner_id
#     #         records = self.env[active_model].browse(active_ids)
#     #         is_exists = self.env['ir.attachment']
#     #         for record in records:
#     #             res_name = record.name.replace('/', '_') if active_model == 'account.move' else record.name.replace('/', '_')
#     #             domain = [('res_id', '=', record.id), ('name', 'like', res_name + '%'), ('res_model', '=', active_model)] 
#     #             is_attachment_exists = Attachment.search(domain, limit=1) if len(active_ids) == 1 else is_exists
#     #             #print ('==sss==',is_attachment_exists)
#     #             if active_model != 'sale.order.line' and not is_attachment_exists:
#     #                 attachments = []
#     #                 template = False
#     #                 if context.get('template'):
#     #                     template = context.get('template')
#     #                 elif active_model == 'sale.order':
#     #                     template = self.env.ref('sale.email_template_edi_sale')
#     #                 elif active_model == 'account.move':
#     #                     template = self.env.ref('account.email_template_edi_invoice')
#     #                 elif active_model == 'purchase.order':
#     #                     if self.env.context.get('send_rfq', False):
#     #                         template = self.env.ref('purchase.email_template_edi_purchase')
#     #                     else:
#     #                         template = self.env.ref('purchase.email_template_edi_purchase_done')
#     #                 elif active_model == 'stock.picking':
#     #                     template = self.env.ref('stock.mail_template_data_delivery_confirmation')
#     #                 elif active_model == 'account.payment':
#     #                     template = self.env.ref('account.mail_template_data_payment_receipt')
#     #                 if not template:
#     #                     break
#     #                 #print ('===',report)
#     #                 report = template.sudo().report_template
#     #                 report_service = report.report_name
    
#     #                 if report.report_type not in ['qweb-html', 'qweb-pdf']:
#     #                     raise UserError(_('Unsupported report type %s found.') % report.report_type)
#     #                 res, format = report._render_qweb_pdf(report, [record.id])
#     #                 #pdf = self.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [order_sudo.id])[0]
#     #                 res = base64.b64encode(res)
#     #                 if not res_name:
#     #                     res_name = 'report.' + report_service
#     #                 ext = "." + format
#     #                 if not res_name.endswith(ext):
#     #                     res_name += ext
#     #                 attachments.append((res_name, res))
#     #                 #print ('==wwww==',attachments)
#     #                 #attachment_ids = []
#     #                 for attachment in attachments:
#     #                     attachment_data = {
#     #                         'name': attachment[0],
#     #                         'store_fname': attachment[0],
#     #                         'datas': attachment[1],
#     #                         'type': 'binary',
#     #                         'res_model': active_model,
#     #                         'res_id': active_id,
#     #                     }
#     #                     is_exists += Attachment.create(attachment_data).id
#     #                 #res, format = report._render_qweb_pdf([record.id])
#     #                 # if active_model == 'account.move':
#     #                 #     report = self.env['ir.actions.report'].sudo()._render_qweb_pdf("account.account_invoices", record.sudo().id)
#     #                 #     filename = res_name + '.' + report[1]
#     #                 #     attachment_data = {
#     #                 #         'name': filename,#attachment[0],
#     #                 #         'store_fname': filename,#attachment[0],
#     #                 #         'datas': base64.b64encode(report[0]),#attachment[1],
#     #                 #         'type': 'binary',
#     #                 #         'res_model': active_model,
#     #                 #         'res_id': active_id,
#     #                 #         'mimetype': 'application/x-pdf',
#     #                 #     }
#     #                 #     is_exists = Attachment.create(attachment_data)
#     #             else:
#     #                 is_exists += is_attachment_exists
#     #         result['model'] = active_model or 'res.partner'
#     #         result['attachment_ids'] = [(6, 0, is_exists.ids)] if is_exists else []
#     #         result['partner_ids'] = [(6, 0, partners.ids)] if partners else []
#     #     return result
    
#     def _prepare_mail_message(self, author_id, chat_id, record, model, body, data, subject, partner_ids, attachment_ids, response, status):
#         # WhatappServer = self.env['mail.message']
#         #for active_id in active_ids:
#         whatsapp_ids = self.env['ir.whatsapp_server'].sudo().search([('status','=','authenticated')], order='sequence asc', limit=1)
#         values = {
#             'whatsapp_server_id': whatsapp_ids.id,
#             'author_id': author_id,
#             'model': model or 'res.partner',
#             'res_id': record,#model and self.ids[0] or False,
#             'body': body,
#             'whatsapp_data': data,
#             'subject': subject or False,
#             'message_type': 'whatsapp',
#             'record_name': subject,
#             'partner_ids': [(4, pid) for pid in partner_ids],
#             'attachment_ids': attachment_ids and [(6, 0, attachment_ids.ids)],
#             #'parent_id': parent_id,
#             #'subtype_id': subtype_id,
#             #'channel_ids': kwargs.get('channel_ids', []),
#             #'add_sign': True,
#             'whatsapp_method': data['method'],
#             'whatsapp_chat_id': chat_id,
#             'whatsapp_response': response,
#             'whatsapp_status': status,
#         }
#         print ('---_prepare_mail_message---',values)
#             #MailMessage += MailMessage.sudo().create(values)
#         return values#MailMessage.sudo().create(values)

#     def _save_attachment_to_public(self, attach):
#         """Save the attachment to a public directory and return the public URL."""
#         import base64
#         import time
        
#         try:
#             # Setup directory
#             base_dir = config.get('data_dir')
#             if not base_dir:
#                 _logger.error('[File Upload] No data_dir configured in Odoo config')
#                 raise UserError(_('Server configuration error: data_dir not set'))
                
#             public_dir = os.path.join(base_dir, 'whatsapp_public_docs')
#             os.makedirs(public_dir, exist_ok=True)
#             _logger.info('[File Upload] Using public directory: %s', public_dir)
            
#             # Generate safe filename
#             filename = f"{attach.id}_{attach.name.replace('/', '_')}"
#             file_path = os.path.join(public_dir, filename)
#             _logger.info('[File Upload] Target file path: %s', file_path)
            
#             # Get file data
#             file_data = attach.datas
#             _logger.info('[File Upload] Initial data check - id=%s, name=%s, has_datas=%s, store_fname=%s',
#                         attach.id, attach.name, bool(file_data), attach.store_fname)
            
#             # Try filestore if datas is empty
#             if not file_data and attach.store_fname:
#                 try:
#                     _logger.info('[File Upload] Reading from filestore: %s', attach.store_fname)
#                     file_data = attach._file_read(attach.store_fname)
#                     if file_data:
#                         _logger.info('[File Upload] Read %d bytes from filestore', len(file_data))
#                     else:
#                         raise UserError(_('Empty file data from filestore for %s') % attach.name)
#                 except Exception as e:
#                     _logger.error('[File Upload] Filestore read failed: %s', str(e))
#                     raise UserError(_('Failed to read file %s from storage: %s') % (attach.name, str(e)))
            
#             if not file_data:
#                 raise UserError(_('No data found for attachment %s') % attach.name)
            
#             # Process file data
#             try:
#                 _logger.info('[File Upload] file_data type: %s', type(file_data))
#                 preview = file_data[:100] if isinstance(file_data, (str, bytes)) else str(file_data)[:100]
#                 _logger.info('[File Upload] file_data preview: %s', preview)
#                 file_bytes = None
#                 if isinstance(file_data, str):
#                     clean_data = file_data.strip()
#                     if clean_data.startswith("b'") and clean_data.endswith("'"):
#                         clean_data = clean_data[2:-1]
#                     clean_data = clean_data.replace('\n', '').replace('\r', '')
#                     file_bytes = base64.b64decode(clean_data)
#                 elif isinstance(file_data, bytes):
#                     # If bytes, check if it's base64-encoded (common for Odoo attachments)
#                     try:
#                         file_bytes = base64.b64decode(file_data, validate=True)
#                         _logger.info('[File Upload] Decoded base64 bytes to binary')
#                     except Exception:
#                         file_bytes = file_data
#                         _logger.info('[File Upload] Used raw bytes as binary')
#                 else:
#                     raise UserError(_('Invalid file data type for %s') % attach.name)
#                 _logger.info('[File Upload] Processed %d bytes of data', len(file_bytes))
#             except Exception as e:
#                 _logger.error('[File Upload] Data conversion failed: %s', str(e))
#                 raise UserError(_('Failed to process file data for %s: %s') % (attach.name, str(e)))
            
#             # Write file
#             try:
#                 with open(file_path, 'wb') as f:
#                     f.write(file_bytes)
                
#                 # Ensure file permissions are set to be readable by the web server
#                 try:
#                     import stat
#                     # Set file permissions to be readable by all (644 in octal)
#                     os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
#                     _logger.info('[File Upload] Set file permissions for %s', file_path)
#                 except Exception as perm_err:
#                     _logger.warning('[File Upload] Could not set file permissions: %s', str(perm_err))
                
#                 # Log detailed file information
#                 file_stat = os.stat(file_path)
#                 _logger.info('[File Upload] Successfully wrote file: %s (%d bytes, created: %s)',
#                             file_path, len(file_bytes), time.ctime(file_stat.st_ctime))
#                 _logger.info('[File Upload] File permissions: %o', file_stat.st_mode & 0o777)
#             except Exception as e:
#                 _logger.error('[File Upload] Failed to write file: %s', str(e))
#                 raise UserError(_('Failed to save file %s: %s') % (attach.name, str(e)))
            
#             # Generate URL
#             try:
#                 base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
#                 if not base_url:
#                     raise UserError(_('Base URL not configured in system parameters'))
                
#                 # Remove trailing slash if present
#                 if base_url.endswith('/'):
#                     base_url = base_url[:-1]
                    
#                 # Generate the public URL
#                 public_url = f"{base_url}/whatsapp_public_docs/{filename}"
#                 _logger.info('[File Upload] Generated public URL: %s', public_url)
                
#                 # Verify URL is accessible (optional check)
#                 try:
#                     import requests
#                     from requests.exceptions import RequestException
#                     # Set a short timeout to avoid blocking
#                     response = requests.head(public_url, timeout=2)
#                     if response.status_code == 200:
#                         _logger.info('[File Upload] URL verification successful: %s (status: %d)', 
#                                     public_url, response.status_code)
#                     else:
#                         _logger.warning('[File Upload] URL verification returned non-200 status: %s (status: %d)', 
#                                        public_url, response.status_code)
#                 except RequestException as req_err:
#                     _logger.warning('[File Upload] URL verification failed: %s (error: %s)', 
#                                    public_url, str(req_err))
#                 except Exception as verify_err:
#                     _logger.warning('[File Upload] URL verification error: %s', str(verify_err))
                
#                 return public_url
#             except Exception as e:
#                 _logger.error('[File Upload] Failed to generate URL: %s', str(e))
#                 raise UserError(_('Failed to generate public URL: %s') % str(e))
                
#         except Exception as e:
#             _logger.error('[File Upload] Critical error processing attachment: %s', str(e))
#             raise UserError(_('Failed to process attachment %s: %s') % (attach.name, str(e)))

#     def whatsapp_message_post_new(self, server, client, _recursion_guard=None):
#         if _recursion_guard is None:
#             _recursion_guard = set()
#         guard_key = (self.id, server.id)
#         if guard_key in _recursion_guard:
#             _logger.error('Recursion detected in whatsapp_message_post_new for self.id=%s, server.id=%s', self.id, server.id)
#             return True
#         _recursion_guard.add(guard_key)
#         try:
#             context = self.env.context
#             opt_out_list = context.get('mass_whatsapp_opt_out_list') or {}
#             message = False
#             MailMessage = self.env['mail.message']
#             get_version = self.env["ir.module.module"].sudo().search([('name','=','base')], limit=1).latest_version
#             # Verify server configuration
#             if not server or not server.session_name:
#                 _logger.error('Invalid WhatsApp server configuration')
#                 raise UserError(_('WhatsApp server configuration is missing or invalid'))

#             # Verify client initialization
#             if not client:
#                 _logger.error('WGApi client not initialized for session: %s', server.session_name)
#                 raise UserError(_('WhatsApp client initialization failed for session: %s') % server.session_name)

#             # Check connection status
#             _logger.info('Checking connection status for session: %s', server.session_name)
#             auth_result = client.auth()
            
#             if not isinstance(auth_result, dict):
#                 _logger.error('Invalid status response type: %s', type(auth_result))
#                 raise UserError(_('Please check your WhatsApp connection in Settings'))
            
#             status = auth_result.get('status')
#             if not status or status != 'connected':
#                 _logger.warning('WhatsApp session not connected - Status: %s', status)
#                 raise UserError(_('Please connect your WhatsApp account in Settings before sending messages'))
            
#             _logger.info('WhatsApp session is connected: %s', server.session_name)
#             for rec in self:
#                 _logger.info('Processing record: %s', rec)
#                 active_model = rec.model
#                 active_ids = context.get('active_ids') or context.get('active_id') or rec.partner_ids.ids
#                 _logger.info('active_model: %s, active_ids: %s', active_model, active_ids)
#                 if rec.whatsapp_type == 'post':
#                     # Determine message body: template or custom message
#                     if rec.send_mode == 'template' and rec.template_id:
#                         message_body = rec.template_id.body_html or rec.template_id.body or ''
#                         _logger.info('Using template for message: %s', rec.template_id.name)
#                     else:
#                         message_body = rec.message or ''
#                         _logger.info('Using custom message field.')
#                     message = message_body.replace("'", '')
#                     partner_ids = context.get('default_partner_ids')
#                     attachment_new_ids = []
#                     _logger.info('[Attachment Logic] Wizard record id: %s', rec.id)
#                     # Process attachments first
#                     attachments = False
#                     try:
#                         # Always use rec.attachment_ids directly, fallback to search if empty
#                         attachments = rec.sudo().attachment_ids
#                         if not attachments:
#                             _logger.warning('[Attachment Logic] attachment_ids empty, searching ir.attachment for res_model=%s, res_id=%s', rec._name, rec.id)
#                             attachments = self.env['ir.attachment'].sudo().search([
#                                 ('res_model', '=', rec._name),
#                                 ('res_id', '=', rec.id)
#                             ])
#                         if not attachments:
#                             _logger.warning('[Attachment Logic] No attachments found after search')
#                     except Exception as e:
#                         _logger.error('[Attachment Logic] Error accessing attachments: %s', e)
#                         raise UserError(_('Error accessing attachments: %s') % str(e))
#                     _logger.info('[Attachment Logic] Attachments found: %s', attachments)
#                     for attach in attachments:
#                         _logger.info('[Attachment Process] id=%s, name=%s, datas type=%s, datas is None=%s', attach.id, attach.name, type(attach.datas), attach.datas is None)
#                         # First try to get data from datas field
#                         file_data = attach.datas
#                         _logger.info('[Attachment Process] Initial data check - id=%s, name=%s, has_datas=%s, store_fname=%s', 
#                                     attach.id, attach.name, bool(file_data), attach.store_fname)

#                         # If datas is empty and we have store_fname, try filestore
#                         if not file_data and attach.store_fname:
#                             try:
#                                 _logger.info('[Attachment Process] Attempting filestore read for id=%s, store_fname=%s', 
#                                             attach.id, attach.store_fname)
#                                 file_data = attach._file_read(attach.store_fname)
#                                 if file_data:
#                                     _logger.info('[Attachment Process] Successfully read %d bytes from filestore', 
#                                                 len(file_data))
#                                 else:
#                                     _logger.error('[Attachment Process] Filestore read returned empty data')
#                             except Exception as e:
#                                 _logger.error('[Attachment Process] Filestore read failed: %s', str(e))
#                                 raise UserError(_('Failed to read attachment %s: %s') % (attach.name, str(e)))

#                         if not file_data:
#                             _logger.error('[Attachment Process] No data found in datas or filestore for id=%s', attach.id)
#                             raise UserError(_('No data found for attachment: %s') % attach.name)
#                         # Always save to public and use the resulting URL
#                         # Save to public directory and get URL
#                         try:
#                             public_url = self._save_attachment_to_public(attach)
#                             if not public_url:
#                                 raise UserError(_('Failed to generate public URL for attachment: %s') % attach.name)
#                             _logger.info('[Attachment Process] Successfully saved to public URL: %s', public_url)
#                         except Exception as e:
#                             _logger.error('[Attachment Process] Failed to save attachment to public: %s', str(e))
#                             raise UserError(_('Failed to process attachment %s: %s') % (attach.name, str(e)))

#                         # Detect mimetype
#                         try:
#                             # Use file extension for more reliable mimetype detection
#                             import mimetypes
#                             ext_mimetype, _ = mimetypes.guess_type(attach.sudo().name)
#                             if ext_mimetype:
#                                 mimetype = ext_mimetype
#                             else:
#                                 if isinstance(file_data, str):
#                                     file_bytes = base64.b64decode(file_data)
#                                     mimetype = guess_mimetype(file_bytes)
#                                 elif isinstance(file_data, bytes):
#                                     mimetype = guess_mimetype(file_data)
#                                 else:
#                                     raise UserError(_('Invalid file data type for attachment: %s') % attach.name)
#                             if not mimetype:
#                                 _logger.warning('[Attachment Process] Could not detect mimetype, defaulting to application/octet-stream')
#                                 mimetype = 'application/octet-stream'
#                             _logger.info('[Attachment Process] Detected mimetype: %s for %s', mimetype, attach.name)
#                         except Exception as e:
#                             _logger.error('[Attachment Process] Mimetype detection failed: %s', str(e))
#                             raise UserError(_('Failed to process file type for %s: %s') % (attach.name, str(e)))
#                         _logger.info('[Attachment Process] name=%s, mimetype=%s, public_url=%s', attach.sudo().name, mimetype, public_url)
#                         vals = {'filename': attach.sudo().name, 'url': public_url, 'mimetype': mimetype}
#                         attachment_new_ids.append(vals)
#                     _logger.info('attachment_new_ids: %s', attachment_new_ids)
#                     _logger.info('rec.attachment_ids: %s', rec.attachment_ids)
#                     # Get all partners first
#                     all_partners = set()
#                     for record in self.env[active_model].browse(active_ids):
#                         origin = link = ''
#                         amount_total = 0
#                         currency_id = False
#                         if active_model != 'res.partner':
#                             if active_model == 'crm.lead':
#                                 link = ''
#                                 origin = record.name
#                                 currency_id = record.company_currency
#                                 amount_total = 0
#                                 partner = record.partner_id or record
#                             elif active_model == 'sale.order':
#                                 link = record.get_portal_url()
#                                 origin = record.name
#                                 currency_id = record.pricelist_id.currency_id
#                                 amount_total = record.amount_total
#                                 partner = record.partner_id
#                             elif active_model == 'purchase.order':
#                                 link = record.get_portal_url()
#                                 origin = record.name
#                                 currency_id = record.currency_id
#                                 amount_total = record.amount_total
#                                 partner = record.partner_id
#                             elif active_model == 'stock.picking':
#                                 link = ''
#                                 origin = record.name
#                                 currency_id = False
#                                 amount_total = 0
#                                 partner = record.partner_id
#                             elif active_model == 'pos.order':
#                                 origin = record.name
#                                 currency_id = record.currency_id
#                                 amount_total = record.amount_total
#                                 partner = record.partner_id
#                             elif active_model == 'account.move':
#                                 link = record.get_portal_url()
#                                 origin = record.name
#                                 currency_id = record.currency_id
#                                 amount_total = record.amount_total
#                                 partner = record.partner_id
#                             if partner_ids:
#                                 partners = self.env['res.partner'].browse(partner_ids)
#                             else:
#                                 partners = record.partner_id
#                         else:
#                             partners = record
                        
#                         # Add partners to the set
#                         if partners:
#                             if isinstance(partners, models.Model):
#                                 all_partners.update(partners.ids)
#                             else:
#                                 all_partners.add(partners.id)
                    
#                     # Now process all unique partners
#                     _logger.info('Processing messages for partners: %s', list(all_partners))
#                     partners = self.env['res.partner'].browse(list(all_partners))
#                         if partners:
#                             for partner in partners:
#                                 _logger.info('--- WhatsApp Number Query Process ---')
#                                 _logger.info('Partner record: %s', partner)
#                                 _logger.info('Partner fields: name=%s, mobile=%s, whatsapp=%s, country_id=%s', partner.name, partner.mobile, partner.whatsapp, partner.country_id)
#                                 whatsapp = partner._formatting_mobile_number()
#                                 _logger.info('Result of _formatting_mobile_number: %s', whatsapp)
#                                 _logger.info('--- End WhatsApp Number Query ---')
#                                 if partner.whatsapp and partner.whatsapp != '0' and whatsapp not in opt_out_list:
#                                     # If attachments exist, send them and skip text message
#                                     if attachment_new_ids:
#                                         sent_files = set()
#                                         for idx, att in enumerate(attachment_new_ids):
#                                             file_key = (partner.id, att.get('filename'))
#                                             if file_key in sent_files:
#                                                 _logger.warning('[WhatsApp] Skipping duplicate send for file: %s to partner: %s', att.get('filename'), partner.id)
#                                                 continue
#                                             sent_files.add(file_key)
#                                             if not att.get('url') or not att.get('filename'):
#                                                 _logger.error('[WhatsApp] Invalid attachment data: %s', att)
#                                                 continue
#                                             mimetype = att.get('mimetype')
#                                             status = 'pending'
#                                             caption = message if idx == 0 else ''
#                                             try:
#                                                 # Constants for file types
#                                                 SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
#                                                 SUPPORTED_DOC_EXTS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.rar'}
                                                
#                                                 # Validate file extension
#                                                 file_ext = os.path.splitext(att.get('filename', '').lower())[1]
#                                                 if not file_ext:
#                                                     raise ValueError(f"Invalid file name format: {att.get('filename')}")
                                                
#                                                 # Determine file type and send accordingly
#                                                 is_image = mimetype and mimetype.startswith('image/') or file_ext in SUPPORTED_IMAGE_EXTS
#                                                 is_document = mimetype and mimetype.startswith('application/') or file_ext in SUPPORTED_DOC_EXTS
                                                
#                                                 if not (is_image or is_document):
#                                                     raise ValueError(f"Unsupported file type: {mimetype or file_ext}")
                                                
#                                                 # Prepare common payload
#                                                 payload = {
#                                                     'session': server.session_name,
#                                                     'to': whatsapp,
#                                                     'text': caption,
#                                                     'is_group': False
#                                                 }
                                                
#                                                 if is_image:
#                                                     _logger.info('[WhatsApp] Sending image: %s to %s', att.get('filename'), whatsapp)
#                                                     payload['image_url'] = att.get('url')
#                                                     response = client.send_image(
#                                                         phone=whatsapp,
#                                                         caption=caption,
#                                                         image_url=att.get('url'),
#                                                         is_group=False
#                                                     )
#                                                 else:  # is_document
#                                                     _logger.info('[WhatsApp] Sending document: %s to %s', att.get('filename'), whatsapp)
#                                                     payload.update({
#                                                         'document_url': att.get('url'),
#                                                         'document_name': att.get('filename')
#                                                     })
#                                                     response = client.send_document(
#                                                         phone=whatsapp,
#                                                         caption=caption,
#                                                         document_url=att.get('url'),
#                                                         document_name=att.get('filename'),
#                                                         is_group=False
#                                                     )
                                                
#                                                 _logger.info('[API CALL] Payload: %s', payload)
#                                                     _logger.info('[API CALL] /message/send-document payload: %s', payload)
#                                                     response = client.send_document(
#                                                         phone=whatsapp,
#                                                         caption=caption,
#                                                         document_url=att.get('url'),
#                                                         document_name=att.get('filename'),
#                                                         is_group=False
#                                                     )
#                                                 else:
#                                                     _logger.warning('[WhatsApp] Unsupported file type: %s (%s)', att.get('filename'), mimetype)
#                                                     response = {'status': 'error', 'message': 'Unsupported file type'}
#                                                 # Validate API response
#                                                 if not response:
#                                                     raise UserError(_('No response received from WhatsApp API'))
                                                
#                                                 _logger.info('[WhatsApp] API response: %s', response)
                                                
#                                                 # Extract status and message from response
#                                                 def extract_from_response(response_dict, key):
#                                                     if not isinstance(response_dict, dict):
#                                                         return None
#                                                     value = response_dict.get(key)
#                                                     if not value and isinstance(response_dict.get('data'), dict):
#                                                         value = response_dict['data'].get(key)
#                                                     return value
                                                
#                                                 resp_status = extract_from_response(response, 'status')
#                                                 error_msg = extract_from_response(response, 'message')
                                                
#                                                 # Process response status
#                                                 if resp_status in ['success', 'PENDING']:
#                                                     status = 'sent'
#                                                     _logger.info('[WhatsApp] Successfully sent file: %s', att.get('filename'))
#                                                 else:
#                                                     status = 'error'
#                                                     error_details = error_msg or 'Unknown error'
#                                                     _logger.error('[WhatsApp] Failed to send file: %s. Error: %s', 
#                                                                  att.get('filename'), error_details)
#                                                     # Don't raise error to allow processing of other files
#                                                     self.env.user.notify_warning(
#                                                         message=_("Failed to send file %(filename)s: %(error)s") % {
#                                                             'filename': att.get('filename'),
#                                                             'error': error_details
#                                                         },
#                                                         title=_('WhatsApp Message Warning')
#                                                     )
#                                             except ValueError as ve:
#                                                 status = 'error'
#                                                 error_msg = str(ve)
#                                                 _logger.error('[WhatsApp] Validation error: %s', error_msg)
#                                                 response = {'status': 'error', 'message': error_msg}
#                                             except requests.RequestException as re:
#                                                 status = 'error'
#                                                 error_msg = f'Network error: {str(re)}'
#                                                 _logger.error('[WhatsApp] Network error: %s', error_msg, exc_info=True)
#                                                 response = {'status': 'error', 'message': error_msg}
#                                             except Exception as e:
#                                                 status = 'error'
#                                                 error_msg = f'Unexpected error: {str(e)}'
#                                                 _logger.error('[WhatsApp] Unexpected error while sending file: %s', error_msg, exc_info=True)
#                                                 response = {'status': 'error', 'message': error_msg}
#                                             finally:
#                                                 if status == 'error':
#                                                     self.env.user.notify_warning(
#                                                         message=_("Error sending file %(filename)s: %(error)s") % {
#                                                             'filename': att.get('filename', 'unknown'),
#                                                             'error': response.get('message', 'Unknown error')
#                                                         },
#                                                         title=_('WhatsApp Message Error')
#                                                     )
#                                             chatID = partner.chat_id if partner.chat_id else whatsapp
#                                             data = {
#                                                 'method': 'send_image' if mimetype and mimetype.startswith('image/') else 'send_document',
#                                                 'phone': whatsapp,
#                                                 'url': att.get('url'),
#                                                 'filename': att.get('filename')
#                                             }
#                                             # Map status to allowed values for mail.message.whatsapp_status
#                                             allowed_status = ['pending', 'send', 'error']
#                                             status_to_save = status
#                                             if status == 'sent':
#                                                 status_to_save = 'send'
#                                             elif status not in allowed_status:
#                                                 status_to_save = 'error'
#                                             vals = self._prepare_mail_message(
#                                                 self.env.user.partner_id.id,
#                                                 chatID,
#                                                 rec.id,
#                                                 active_model,
#                                                 texttohtml.formatHtml(caption),
#                                                 data,
#                                                 rec.subject,
#                                                 [partner.id],
#                                                 rec.attachment_ids,
#                                                 response,
#                                                 status_to_save
#                                             )
#                                             message_id = MailMessage.sudo().create(vals)
#                                             _logger.info('[WhatsApp] Created mail message: %s', message_id)
#                             else:
#                                 try:
#                                     payload = {
#                                         'session': server.session_name,
#                                         'to': whatsapp,
#                                         'text': message,
#                                         'is_group': False
#                                     }
#                                     _logger.info('[API CALL] /message/send-text payload: %s', payload)
#                                     send_message = client.send_message(phone=whatsapp, message=message, is_group=False)
#                                     _logger.info('WGApi.send_message returned: %s', send_message)
#                                     status = 'send' if send_message.get('status') == 'success' else 'error'
#                                 except Exception as e:
#                                     send_message = {'error': str(e)}
#                                     status = 'error'
#                                     _logger.error('Error sending text message: %s', e)
#                                 chatID = partner.chat_id if partner.chat_id else whatsapp
#                                 vals = self._prepare_mail_message(self.env.user.partner_id.id, chatID, rec.id, active_model, texttohtml.formatHtml(message), send_message, rec.subject, [partner.id], [], send_message, status)
#                                 MailMessage += MailMessage.sudo().create(vals)
#                     # Build a queue of partners to process
#                     partner_queue = list(rec.partner_ids)
#                     while partner_queue:
#                         partner = partner_queue.pop(0)
#                         _logger.info('--- WhatsApp Number Query Process ---')
#                         _logger.info('Partner record: %s', partner)
#                         _logger.info('Partner fields: name=%s, mobile=%s, whatsapp=%s, country_id=%s', partner.name, partner.mobile, partner.whatsapp, partner.country_id)
#                         whatsapp = partner._formatting_mobile_number()
#                         _logger.info('Result of _formatting_mobile_number: %s', whatsapp)
#                         _logger.info('--- End WhatsApp Number Query ---')
#                         if partner.whatsapp and partner.whatsapp != '0' and whatsapp not in opt_out_list:
#                             if attachment_new_ids:
#                                 sent_files = set()
#                                 for idx, att in enumerate(attachment_new_ids):
#                                     file_key = (partner.id, att.get('filename'))
#                                     if file_key in sent_files:
#                                         _logger.warning('[WhatsApp] Skipping duplicate send for file: %s to partner: %s', att.get('filename'), partner.id)
#                                         continue
#                                     sent_files.add(file_key)
#                                     if not att.get('url') or not att.get('filename'):
#                                         _logger.error('[WhatsApp] Invalid attachment data: %s', att)
#                                         continue
#                                     mimetype = att.get('mimetype')
#                                     status = 'pending'
#                                     caption = message if idx == 0 else ''
#                                     try:
#                                         image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
#                                         doc_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.rar']
#                                         file_ext = os.path.splitext(att.get('filename', '').lower())[1]
#                                         if mimetype and (mimetype.startswith('image/') or file_ext in image_exts):
#                                             _logger.info('[WhatsApp] Sending image: %s to %s', att.get('filename'), whatsapp)
#                                             payload = {
#                                                 'session': server.session_name,
#                                                 'to': whatsapp,
#                                                 'text': caption,
#                                                 'image_url': att.get('url'),
#                                                 'is_group': False
#                                             }
#                                             _logger.info('[API CALL] /message/send-image payload: %s', payload)
#                                             response = client.send_image(
#                                                 phone=whatsapp,
#                                                 caption=caption,
#                                                 image_url=att.get('url'),
#                                                 is_group=False
#                                             )
#                                         elif mimetype and (mimetype.startswith('application/') or file_ext in doc_exts):
#                                             _logger.info('[WhatsApp] Sending document: %s to %s', att.get('filename'), whatsapp)
#                                             payload = {
#                                                 'session': server.session_name,
#                                                 'to': whatsapp,
#                                                 'text': caption,
#                                                 'document_url': att.get('url'),
#                                                 'document_name': att.get('filename'),
#                                                 'is_group': False
#                                             }
#                                             _logger.info('[API CALL] /message/send-document payload: %s', payload)
#                                             response = client.send_document(
#                                                 phone=whatsapp,
#                                                 caption=caption,
#                                                 document_url=att.get('url'),
#                                                 document_name=att.get('filename'),
#                                                 is_group=False
#                                             )
#                                         else:
#                                             _logger.warning('[WhatsApp] Unsupported file type: %s (%s)', att.get('filename'), mimetype)
#                                             response = {'status': 'error', 'message': 'Unsupported file type'}
#                                         if not response:
#                                             raise UserError(_('No response received from WhatsApp API'))
#                                         _logger.info('[WhatsApp] API response: %s', response)
#                                         resp_status = response.get('status')
#                                         if not resp_status and isinstance(response.get('data'), dict):
#                                             resp_status = response['data'].get('status')
#                                         if resp_status in ['success', 'PENDING']:
#                                             status = 'sent'
#                                             _logger.info('[WhatsApp] Successfully sent file: %s', att.get('filename'))
#                                         else:
#                                             error_msg = response.get('message') or (response.get('data', {}).get('message') if isinstance(response.get('data'), dict) else None) or 'Unknown error'
#                                             _logger.error('[WhatsApp] Failed to send file: %s. Error: %s', att.get('filename'), error_msg)
#                                             status = 'error'
#                                     except Exception as e:
#                                         status = 'error'
#                                         response = {'error': str(e)}
#                                         _logger.error('[WhatsApp] Error sending file: %s', e)
#                                     chatID = partner.chat_id if partner.chat_id else whatsapp
#                                     data = {
#                                         'method': 'send_image' if mimetype and mimetype.startswith('image/') else 'send_document',
#                                         'phone': whatsapp,
#                                         'url': att.get('url'),
#                                         'filename': att.get('filename')
#                                     }
#                                     # Map status to allowed values for mail.message.whatsapp_status
#                                     allowed_status = ['pending', 'send', 'error']
#                                     status_to_save = status
#                                     if status == 'sent':
#                                         status_to_save = 'send'
#                                     elif status not in allowed_status:
#                                         status_to_save = 'error'
#                                     vals = self._prepare_mail_message(
#                                         self.env.user.partner_id.id,
#                                         chatID,
#                                         rec.id,
#                                         active_model,
#                                         texttohtml.formatHtml(caption),
#                                         data,
#                                         rec.subject,
#                                         [partner.id],
#                                         rec.attachment_ids,
#                                         response,
#                                         status_to_save
#                                     )
#                                     message_id = MailMessage.sudo().create(vals)
#                                     _logger.info('[WhatsApp] Created mail message: %s', message_id)
#                             else:
#                                 try:
#                                     payload = {
#                                         'session': server.session_name,
#                                         'to': whatsapp,
#                                         'text': message,
#                                         'is_group': False
#                                     }
#                                     _logger.info('[API CALL] /message/send-text payload: %s', payload)
#                                     send_message = client.send_message(phone=whatsapp, message=message, is_group=False)
#                                     _logger.info('WGApi.send_message returned: %s', send_message)
#                                     status = 'send' if send_message.get('status') == 'success' else 'error'
#                                 except Exception as e:
#                                     send_message = {'error': str(e)}
#                                     status = 'error'
#                                     _logger.error('Error sending text message: %s', e)
#                                 chatID = partner.chat_id if partner.chat_id else whatsapp
#                                 vals = self._prepare_mail_message(self.env.user.partner_id.id, chatID, rec.id, active_model, texttohtml.formatHtml(message), send_message, rec.subject, [partner.id], [], send_message, status)
#                                 MailMessage += MailMessage.sudo().create(vals)
#         except Exception as e:
#             _logger.warning('Whatsapp Authentication Failed or message send error!\nConfigure Whatsapp Configuration in General Setting. Error: %s', str(e))
#         return True

#     def whatsapp_message_post(self):
#         """Button action to send WhatsApp message from wizard UI."""
#         _logger.info('whatsapp_message_post called')
#         # Find the first connected WhatsApp server
#         whatsapp_ids = self.env['ir.whatsapp_server'].search([('connection_status', '=', 'connected')], limit=1)
#         if not whatsapp_ids:
#             _logger.error('No connected WhatsApp server found.')
#             raise UserError(_('No connected WhatsApp server found.'))
#         for wserver in whatsapp_ids:
#             client = wserver._get_wgapi_client()
#             # Call synchronously for debugging
#             self.whatsapp_message_post_new(wserver, client)
#         _logger.info('whatsapp_message_post finished')
#         return {'type': 'ir.actions.act_window_close'}



# See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import api, fields, models, sql_db, _, tools, Command
from odoo.tools.misc import formatLang, get_lang, format_amount
from odoo.exceptions import ValidationError, RedirectWarning
from odoo.tools.mimetypes import guess_mimetype
from datetime import datetime
from odoo.tools import pycompat
from odoo.exceptions import UserError
import html2text
from odoo.tools import is_html_empty
from odoo.addons.mail.tools.parser import parse_res_ids
from ..wgapi import texttohtml
from odoo.tools.misc import html_escape
import requests
import json
import ast
import base64
import threading
import time
import logging
import os
from odoo.tools import config

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
    composition_batch = fields.Boolean(
        'Batch composition', compute='_compute_composition_batch')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    subject = fields.Char('Subject')
    message = fields.Text(
        'Contents',
        compute='_compute_body', readonly=False, store=True)
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
        return mail_template\
            ._render_field(field, rec.ids, **kwargs)[rec._origin.id]

    @api.depends('composition_mode', 'model', 'res_ids', 'template_id')
    def _compute_body(self):
        for composer in self:
            rec = composer._get_active_records()
            if composer.template_id and rec:
                composer.message = html2text.html2text(self._get_default_mail_body(rec, composer.template_id)) if composer.template_id.body_html else 'Sample Message'
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

    def _generate_template_for_composer(self, res_ids, render_fields,
                                        find_or_create_partners=True):
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
        values = {
            'whatsapp_server_id': self.env['ir.whatsapp_server'].sudo().search([('status','=','authenticated')], order='sequence asc', limit=1).id,
            'author_id': author_id,
            'model': model or 'res.partner',
            'res_id': record,
            'body': body,
            'whatsapp_data': data,
            'subject': subject or False,
            'message_type': 'whatsapp',
            'record_name': subject,
            'partner_ids': [(4, pid) for pid in partner_ids],
            'attachment_ids': attachment_ids and [(6, 0, attachment_ids.ids)],
            'whatsapp_method': data.get('method'),
            'whatsapp_chat_id': chat_id,
            'whatsapp_response': response,
            'whatsapp_status': status,
        }
        _logger.debug('Prepared mail message values: %s', values)
        return values

    def _save_attachment_to_public(self, attach):
        """Save the attachment to a public directory and return the public URL."""
        try:
            base_dir = config.get('data_dir')
            if not base_dir:
                _logger.error('No data_dir configured in Odoo config')
                raise UserError(_('Server configuration error: data_dir not set'))
                
            public_dir = os.path.join(base_dir, 'whatsapp_public_docs')
            os.makedirs(public_dir, exist_ok=True)
            
            filename = f"{attach.id}_{attach.name.replace('/', '_')}"
            file_path = os.path.join(public_dir, filename)
            
            file_data = attach.datas
            if not file_data and attach.store_fname:
                try:
                    file_data = attach._file_read(attach.store_fname)
                    if not file_data:
                        raise UserError(_('Empty file data from filestore for %s') % attach.name)
                except Exception as e:
                    raise UserError(_('Failed to read file %s from storage: %s') % (attach.name, str(e)))
            
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
            except Exception:
                _logger.warning('Could not set file permissions for %s', file_path)
            
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if not base_url:
                raise UserError(_('Base URL not configured in system parameters'))
                
            if base_url.endswith('/'):
                base_url = base_url[:-1]
                
            public_url = f"{base_url}/whatsapp_public_docs/{filename}"
            return public_url
                
        except Exception as e:
            _logger.error('Error processing attachment: %s', str(e))
            raise UserError(_('Failed to process attachment %s: %s') % (attach.name, str(e)))

    def whatsapp_message_post_new(self, server, client, _recursion_guard=None):
        if _recursion_guard is None:
            _recursion_guard = set()
        guard_key = (self.id, server.id)
        if guard_key in _recursion_guard:
            _logger.error('Recursion detected in whatsapp_message_post_new for self.id=%s, server.id=%s', self.id, server.id)
            return True
        _recursion_guard.add(guard_key)
        
        try:
            context = self.env.context
            opt_out_list = context.get('mass_whatsapp_opt_out_list') or {}
            MailMessage = self.env['mail.message']
            
            if not server or not server.session_name:
                raise UserError(_('WhatsApp server configuration is missing or invalid'))

            if not client:
                raise UserError(_('WhatsApp client initialization failed for session: %s') % server.session_name)

            auth_result = client.auth()
            if not isinstance(auth_result, dict):
                raise UserError(_('Please check your WhatsApp connection in Settings'))
            
            status = auth_result.get('status')
            if not status or status != 'connected':
                raise UserError(_('Please connect your WhatsApp account in Settings before sending messages'))
            
            for rec in self:
                active_model = rec.model
                active_ids = context.get('active_ids') or context.get('active_id') or rec.partner_ids.ids
                
                if rec.whatsapp_type == 'post':
                    if rec.send_mode == 'template' and rec.template_id:
                        message_body = rec.template_id.body_html or rec.template_id.body or ''
                    else:
                        message_body = rec.message or ''
                    message = message_body.replace("'", '')
                    
                    attachment_new_ids = []
                    attachments = rec.sudo().attachment_ids
                    if not attachments:
                        attachments = self.env['ir.attachment'].sudo().search([
                            ('res_model', '=', rec._name),
                            ('res_id', '=', rec.id)
                        ])
                    
                    for attach in attachments:
                        try:
                            public_url = self._save_attachment_to_public(attach)
                            mimetype = guess_mimetype(base64.b64decode(attach.datas)) if attach.datas else 'application/octet-stream'
                            attachment_new_ids.append({
                                'filename': attach.sudo().name,
                                'url': public_url,
                                'mimetype': mimetype
                            })
                        except Exception as e:
                            _logger.error('Failed to process attachment: %s', str(e))
                            continue
                    
                    all_partners = set()
                    for record in self.env[active_model].browse(active_ids):
                        if active_model != 'res.partner':
                            partner = record.partner_id
                        else:
                            partner = record
                        
                        if partner:
                            all_partners.add(partner.id)
                    
                    partners = self.env['res.partner'].browse(list(all_partners))
                    for partner in partners:
                        whatsapp = partner._formatting_mobile_number()
                        if partner.whatsapp and partner.whatsapp != '0' and whatsapp not in opt_out_list:
                            if attachment_new_ids:
                                for idx, att in enumerate(attachment_new_ids):
                                    try:
                                        caption = message if idx == 0 else ''
                                        if att['mimetype'].startswith('image/'):
                                            response = client.send_image(
                                                phone=whatsapp,
                                                caption=caption,
                                                image_url=att['url'],
                                                is_group=False
                                            )
                                        else:
                                            response = client.send_document(
                                                phone=whatsapp,
                                                caption=caption,
                                                document_url=att['url'],
                                                document_name=att['filename'],
                                                is_group=False
                                            )
                                        
                                        status = 'sent' if response.get('status') in ['success', 'PENDING'] else 'error'
                                    except Exception as e:
                                        status = 'error'
                                        response = {'error': str(e)}
                                        _logger.error('Error sending attachment: %s', str(e))
                                    
                                    chatID = partner.chat_id if partner.chat_id else whatsapp
                                    data = {
                                        'method': 'send_image' if att['mimetype'].startswith('image/') else 'send_document',
                                        'phone': whatsapp,
                                        'url': att['url'],
                                        'filename': att['filename']
                                    }
                                    vals = self._prepare_mail_message(
                                        self.env.user.partner_id.id,
                                        chatID,
                                        rec.id,
                                        active_model,
                                        texttohtml.formatHtml(caption),
                                        data,
                                        rec.subject,
                                        [partner.id],
                                        rec.attachment_ids,
                                        response,
                                        'send' if status == 'sent' else 'error'
                                    )
                                    MailMessage.sudo().create(vals)
                            else:
                                try:
                                    response = client.send_message(
                                        phone=whatsapp,
                                        message=message,
                                        is_group=False
                                    )
                                    status = 'send' if response.get('status') == 'success' else 'error'
                                except Exception as e:
                                    response = {'error': str(e)}
                                    status = 'error'
                                    _logger.error('Error sending text message: %s', str(e))
                                
                                chatID = partner.chat_id if partner.chat_id else whatsapp
                                vals = self._prepare_mail_message(
                                    self.env.user.partner_id.id,
                                    chatID,
                                    rec.id,
                                    active_model,
                                    texttohtml.formatHtml(message),
                                    response,
                                    rec.subject,
                                    [partner.id],
                                    [],
                                    response,
                                    status
                                )
                                MailMessage.sudo().create(vals)
        except Exception as e:
            _logger.error('WhatsApp message sending failed: %s', str(e))
            raise UserError(_('WhatsApp message sending failed: %s') % str(e))
        
        return True

    def whatsapp_message_post(self):
        _logger.info('whatsapp_message_post called')
        whatsapp_ids = self.env['ir.whatsapp_server'].search([('connection_status', '=', 'connected')], limit=1)
        if not whatsapp_ids:
            raise UserError(_('No connected WhatsApp server found.'))
        
        for wserver in whatsapp_ids:
            client = wserver._get_wgapi_client()
            self.whatsapp_message_post_new(wserver, client)
        
        return {'type': 'ir.actions.act_window_close'}