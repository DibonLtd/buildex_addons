
from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    referral_code = fields.Char(copy=False)
    referral_points = fields.Float(default=0.0)
    referral_url = fields.Char(compute='_compute_referral_url')
    referral_qr = fields.Binary(compute='_compute_referral_qr')
    # referral_qr = fields.Binary(compute="_compute_referral_qr", store=True)
    is_referrer = fields.Boolean(string="Enable Influencer Program",default=False)

    influencer_state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True)

    # NEW: commission wallet

    influencer_currency_id = fields.Many2one(
        'res.currency',
        string="Wallet Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    influencer_wallet = fields.Monetary(
        string="Influencer Wallet",
        currency_field='influencer_currency_id',
        tracking=True
    )

    applied_as_influencer = fields.Boolean(
        string="Applied as Influencer",
        default=False,
        index=True
    )

    influencer_state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Influencer Status", default='draft', tracking=True)

    influencer_application_note = fields.Text(
        string="Influencer Application Note"
    )
    influencer_facebook_link = fields.Char(string="Facebook Link")
    influencer_instagram_link = fields.Char(string="Instagram Link")
    influencer_x_link = fields.Char(string="X Link")
    influencer_linkedin_link = fields.Char(string="LinkedIn Link")
    influencer_youtube_link = fields.Char(string="YouTube Link")
    influencer_tiktok_link = fields.Char(string="TikTok Link")

    # -- Shared personal details (common partner fields) --
    # Uses existing: country_id (nationality), city (hometown)
    id_number = fields.Char(string="ID / Passport Number")
    birthdate = fields.Date(string="Date of Birth")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string="Gender")
    county = fields.Selection([
        ('mombasa', 'Mombasa'),
        ('kwale', 'Kwale'),
        ('kilifi', 'Kilifi'),
        ('tana_river', 'Tana River'),
        ('lamu', 'Lamu'),
        ('taita_taveta', 'Taita/Taveta'),
        ('garissa', 'Garissa'),
        ('wajir', 'Wajir'),
        ('mandera', 'Mandera'),
        ('marsabit', 'Marsabit'),
        ('isiolo', 'Isiolo'),
        ('meru', 'Meru'),
        ('tharaka_nithi', 'Tharaka-Nithi'),
        ('embu', 'Embu'),
        ('kitui', 'Kitui'),
        ('machakos', 'Machakos'),
        ('makueni', 'Makueni'),
        ('nyandarua', 'Nyandarua'),
        ('nyeri', 'Nyeri'),
        ('kirinyaga', 'Kirinyaga'),
        ('muranga', "Murang'a"),
        ('kiambu', 'Kiambu'),
        ('turkana', 'Turkana'),
        ('west_pokot', 'West Pokot'),
        ('samburu', 'Samburu'),
        ('trans_nzoia', 'Trans Nzoia'),
        ('uasin_gishu', 'Uasin Gishu'),
        ('elgeyo_marakwet', 'Elgeyo/Marakwet'),
        ('nandi', 'Nandi'),
        ('baringo', 'Baringo'),
        ('laikipia', 'Laikipia'),
        ('nakuru', 'Nakuru'),
        ('narok', 'Narok'),
        ('kajiado', 'Kajiado'),
        ('kericho', 'Kericho'),
        ('bomet', 'Bomet'),
        ('kakamega', 'Kakamega'),
        ('vihiga', 'Vihiga'),
        ('bungoma', 'Bungoma'),
        ('busia', 'Busia'),
        ('siaya', 'Siaya'),
        ('kisumu', 'Kisumu'),
        ('homa_bay', 'Homa Bay'),
        ('migori', 'Migori'),
        ('kisii', 'Kisii'),
        ('nyamira', 'Nyamira'),
        ('nairobi', 'Nairobi City'),
    ], string="County")

    # -- Influencer application fields --
    influencer_join_reason = fields.Selection([
        ('earn', 'Earn'),
        ('learn', 'Learn'),
        ('grow_career', 'Grow my career'),
        ('leisure', 'Leisure'),
        ('grow_social', 'Grow social media'),
        ('other', 'Other'),
    ], string="Reason for Joining")
    influencer_experience_years = fields.Selection([
        ('under_1', 'Under 1 year'),
        ('1', '1 year'),
        ('2', '2 years'),
        ('3_plus', '3+'),
    ], string="Years of Influencer Experience")
    influencer_referral_source = fields.Selection([
        ('social_media', 'Social Media'),
        ('salesperson', 'Salesperson'),
        ('media', 'Media'),
        ('friend', 'Friend'),
        ('referred', 'Referred'),
        ('website', 'Website'),
        ('other', 'Other'),
    ], string="Source of Referral")
    influencer_construction_knowledge = fields.Text(string="Construction Material Knowledge")
    influencer_payment_account = fields.Char(string="Payment Account Details")
    influencer_convicted = fields.Boolean(string="Has Been Convicted", default=False)
    influencer_conviction_details = fields.Text(string="Conviction Details")
    influencer_terms_accepted = fields.Boolean(string="Terms & Conditions Accepted", default=False)

    # Communication preferences (multi-select via booleans)
    comm_mode_call = fields.Boolean(string='Phone Call', default=False)
    comm_mode_whatsapp = fields.Boolean(string='WhatsApp', default=False)
    comm_mode_sms = fields.Boolean(string='SMS', default=False)

    # Visitor location captured via browser (GPS / network / IP fallback)
    visitor_latitude = fields.Float(string="Visitor Latitude", digits=(10, 7))
    visitor_longitude = fields.Float(string="Visitor Longitude", digits=(10, 7))
    visitor_city = fields.Char(string="Visitor City")
    visitor_location_source = fields.Selection([
        ('gps', 'GPS (high accuracy)'),
        ('network', 'Network/WiFi'),
        ('ip', 'IP Geolocation'),
    ], string="Location Source")

    # Referral code persisted to DB for cross-device / cross-browser session restore
    tracked_referral_code = fields.Char(string='Tracked Referral Code', copy=False)
    tracked_referral_code_expiry = fields.Datetime(string='Referral Code Expiry', copy=False)

    commission_plan_id = fields.Many2one(
        'influencer.commission.plan'
    )

    referred_by_id = fields.Many2one(
        'res.partner',
        string='Referred By',
        help='The influencer whose referral link this user signed up through',
        index=True,
    )

    topline_referral_code = fields.Char(
        string='Topline Code',
        copy=False,
        help='Unique code given to this influencer to share when recruiting new influencers. '
             'Different from the product referral code.',
    )

    is_topline = fields.Boolean(
        string='Enable Topline',
        default=False,
        help='When enabled, this approved influencer can recruit new influencers using '
             'their topline code and earn topline bonuses. Must be set manually by admin.',
    )

    topline_id = fields.Many2one(
        'res.partner',
        string='Topline Mentor',
        domain=[('is_referrer', '=', True)],
        help='The influencer who introduced this person to the program via topline code.',
    )

    topline_referral_ids = fields.One2many(
        'res.partner',
        'topline_id',
        string='Referred Influencers',
    )


    wallet_balance = fields.Monetary(
        compute='_compute_wallet_balance',
        currency_field='currency_id'
    )

    wallet_transaction_ids = fields.One2many(
        'influencer.wallet.transaction',
        'partner_id'
    )
    referral_visit_stat_ids = fields.One2many(
        'influencer.referral.visit.stat',
        'partner_id',
        string="Referral Daily Visits",
    )
    referral_visit_log_ids = fields.One2many(
        'influencer.referral.visit.log',
        'partner_id',
        string="Visitor Location Log",
    )
    referral_total_visits = fields.Integer(
        compute='_compute_referral_visit_metrics',
        string="Total Referral Visits",
    )
    referral_today_visits = fields.Integer(
        compute='_compute_referral_visit_metrics',
        string="Today's Referral Visits",
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )


    def _compute_wallet_balance(self):
        for partner in self:
            credits = self.env['influencer.wallet.transaction'].search([
                ('partner_id', '=', partner.id),
                ('transaction_type', '=', 'credit')
            ])

            debits = self.env['influencer.wallet.transaction'].search([
                ('partner_id', '=', partner.id),
                ('transaction_type', '=', 'debit')
            ])

            total_credit = sum(credits.mapped('amount'))
            total_debit = sum(debits.mapped('amount'))

            partner.wallet_balance = total_credit - total_debit

    def _compute_referral_visit_metrics(self):
        stats_model = self.env['influencer.referral.visit.stat'].sudo()
        today = fields.Date.context_today(self)

        totals = {
            row['partner_id'][0]: int(row['visit_count'])
            for row in stats_model.read_group(
                [('partner_id', 'in', self.ids)],
                ['partner_id', 'visit_count:sum'],
                ['partner_id'],
                lazy=False,
            )
            if row.get('partner_id')
        }

        today_totals = {
            row['partner_id'][0]: int(row['visit_count'])
            for row in stats_model.read_group(
                [('partner_id', 'in', self.ids), ('date', '=', today)],
                ['partner_id', 'visit_count:sum'],
                ['partner_id'],
                lazy=False,
            )
            if row.get('partner_id')
        }

        for partner in self:
            partner.referral_total_visits = totals.get(partner.id, 0)
            partner.referral_today_visits = today_totals.get(partner.id, 0)


    # def _compute_wallet_balance(self):
    #     tx_model = self.env['influencer.wallet.transaction']

    #     grouped = tx_model.read_group(
    #         [('partner_id', 'in', self.ids)],
    #         ['amount:sum', 'partner_id', 'transaction_type'],
    #         ['partner_id', 'transaction_type']
    #     )

    #     result = {partner.id: 0.0 for partner in self}

    #     for group in grouped:
    #         partner_id = group.get('partner_id')
    #         tx_type = group.get('transaction_type')
    #         amount = group.get('amount_sum', 0.0)

    #         if not partner_id or not tx_type:
    #             continue

    #         pid = partner_id[0]

    #         if tx_type == 'credit':
    #             result[pid] += amount
    #         elif tx_type == 'debit':
    #             result[pid] -= amount

    #     for partner in self:
    #         partner.wallet_balance = result.get(partner.id, 0.0)





    @api.constrains('influencer_state', 'commission_plan_id')
    def _check_plan_required(self):
        for rec in self:
            if rec.influencer_state == 'approved' and not rec.commission_plan_id:
                raise ValidationError("Approved influencers must have a commission plan.Select  commission plan then approve.")



    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_referrer"):
                if not vals.get("referral_code"):
                    vals["referral_code"] = self.env["ir.sequence"].next_by_code("referral.code")
                if not vals.get("topline_referral_code"):
                    vals["topline_referral_code"] = self.env["ir.sequence"].next_by_code("topline.referral.code")
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for partner in self:
            if vals.get("is_referrer"):
                if not partner.referral_code:
                    partner.referral_code = self.env["ir.sequence"].next_by_code("referral.code")
                    partner._compute_referral_url()
                    partner._compute_referral_qr()
                if not partner.topline_referral_code:
                    partner.topline_referral_code = self.env["ir.sequence"].next_by_code("topline.referral.code")
        return res




    @api.depends("referral_code", "is_referrer")
    def _compute_referral_url(self):
        """
        Compute the referral URL that users can share.
        Uses the new /referral controller to store code in session first.
        """
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for partner in self:
            if partner.is_referrer and partner.referral_code:
                # New referral link
                partner.referral_url = f"{base_url}/referral?ref={partner.referral_code}&next=/shop"
            else:
                partner.referral_url = False


    @api.depends("referral_url", "is_referrer")
    def _compute_referral_qr(self):
        Company = self.env.company

        for partner in self:
            if not partner.is_referrer or not partner.referral_url:
                partner.referral_qr = False
                continue
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(partner.referral_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

            # ---- Logo with white background ----
            if Company.logo:
                logo_bytes = base64.b64decode(Company.logo)
                logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")

                qr_w, qr_h = qr_img.size
                logo_size = qr_w // 4
                logo.thumbnail((logo_size, logo_size), Image.LANCZOS)

                # White background box
                bg_size = (logo.size[0] + 20, logo.size[1] + 20)
                bg = Image.new("RGBA", bg_size, (255, 255, 255, 255))

                bg_x = (qr_w - bg_size[0]) // 2
                bg_y = (qr_h - bg_size[1]) // 2
                qr_img.paste(bg, (bg_x, bg_y), bg)

                logo_x = bg_x + 10
                logo_y = bg_y + 10
                qr_img.paste(logo, (logo_x, logo_y), logo)

            # ---- Add company name text below QR ----
            company_name = Company.name or ""
            padding = 40

            final_img = Image.new(
                "RGBA",
                (qr_img.width, qr_img.height + padding),
                "white"
            )
            final_img.paste(qr_img, (0, 0))

            draw = ImageDraw.Draw(final_img)

            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            except:
                font = ImageFont.load_default()

            # Pillow-compatible text size calculation
            bbox = draw.textbbox((0, 0), company_name, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            text_x = (final_img.width - text_w) // 2
            text_y = qr_img.height + 5

            draw.text((text_x, text_y), company_name, fill="black", font=font)


            # ---- Save binary ----
            buffer = BytesIO()
            final_img.save(buffer, format="PNG")
            partner.referral_qr = base64.b64encode(buffer.getvalue())


    def action_visit_tiktok(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_tiktok_link, 'target': 'new'}

    def action_visit_facebook(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_facebook_link, 'target': 'new'}

    def action_visit_instagram(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_instagram_link, 'target': 'new'}

    def action_visit_x(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_x_link, 'target': 'new'}

    def action_visit_linkedin(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_linkedin_link, 'target': 'new'}

    def action_visit_youtube(self):
        return {'type': 'ir.actions.act_url', 'url': self.influencer_youtube_link, 'target': 'new'}

    def action_approve_influencer(self):
        for partner in self:
            partner.write({
                'influencer_state': 'approved',
                'is_referrer': True,  # triggers existing QR logic
            })
            partner.message_post(
                body="Influencer application approved."
            )

    def action_reject_influencer(self, reason=None):
        for partner in self:
            partner.write({
                'influencer_state': 'rejected',
                'is_referrer': False,
                'influencer_application_note': reason or '',
            })
            partner.message_post(
                body="Influencer application rejected."
            )
