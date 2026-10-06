from odoo import _, http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request


class AuthSignupHomeKE(AuthSignupHome):

    def _get_available_delivery_towns(self):
        kenya = request.env["res.country"].sudo().search([("code", "=", "KE")], limit=1)
        if not kenya:
            return request.env["res.country.state"]
        return request.env["res.country.state"].sudo().search(
            [("country_id", "=", kenya.id), ("is_delivery_town", "=", True)],
            order="name asc",
        )

    @http.route("/web/signup", type="http", auth="public", website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        response = super().web_auth_signup(*args, **kw)
        if hasattr(response, "qcontext"):
            qcontext = response.qcontext
            qcontext["available_delivery_towns"] = self._get_available_delivery_towns()
            is_referral_signup = bool(request.session.get("referral_code")) or kw.get("from_referral")
            qcontext["is_referral_signup"] = bool(is_referral_signup)
            qcontext["default_delivery_town_id"] = kw.get("default_delivery_town_id")
            qcontext["from_referral"] = kw.get("from_referral")
        return response

    def do_signup(self, qcontext):
        town_id = request.params.get("default_delivery_town_id")
        town = request.env["res.country.state"]

        if town_id:
            try:
                town = request.env["res.country.state"].sudo().browse(int(town_id)).exists()
            except (TypeError, ValueError):
                town = request.env["res.country.state"]

        if town and not town.is_delivery_town:
            raise UserError(_("Selected town is not available for delivery."))

        super().do_signup(qcontext)

        if town:
            request.env.user.partner_id.sudo().write(
                {
                    "country_id": town.country_id.id,
                    "state_id": town.id,
                }
            )
