/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SignUpFormExtension = publicWidget.Widget.extend({
    selector: '.oe_signup_form_mobile, .oe_reset_password_form',
    events: {
        'click .sent-otp': '_onClick',
        'change .check_login': '_onClickCheck',
        'click button[type="submit"]': '_onSubmitClick',
    },
    init() {
        this._super(...arguments);
        this._locSource = null; // track which source filled the location
    },

    _onClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.$('.sign-up').removeAttr('disabled');
        this.$('.sent-otp').attr('disabled', 'disabled');
        $(".login_mobile").attr('readonly', 'readonly');
        const CountryCode = $(".div_code")[0].value;
        const Mobile = $(".login_mobile")[0].value;
        let OTP = '';
        var digits = '0123456789';
        for (let i = 0; i < 4; i++) {
            OTP += digits[Math.floor(Math.random() * 10)];
        }
        window.localStorage.setItem("OTP", OTP);
        rpc('/web/send_otp', {
            'country_code': CountryCode,
            'mobile': Mobile,
            'otp': OTP,
        });
    },

    _onSubmitClick: function (ev) {
        this.$('.sent-otp').removeAttr('disabled');
        let otp_val = $("#sms_otp_verify")[0].value;
        let OTP = window.localStorage.getItem("OTP");
        if (OTP && otp_val && OTP != otp_val) {
            ev.preventDefault();
            alert('OTP is not matching');
        }
    },

    _onClickCheck: function (ev) {
        let checked = $('.check_login')[0].checked;
        if (checked) {
            $('#login_mail')[0].value = $(".field-login")[0].children[1].value;
        }
    },

    start: function () {
        this._super(...arguments);
        this._captureLocation();
        this._bindContactPrefHighlight();
    },

    // ── Helpers ───────────────────────────────────────────────────────

    _setLocation: function (lat, lng, source, city) {
        // Only overwrite with a less accurate source if nothing better is set
        var priority = { gps: 3, network: 2, ip: 1 };
        var current = priority[this._locSource] || 0;
        var incoming = priority[source] || 0;
        if (incoming < current) return;

        var latEl = document.getElementById('visitor_latitude');
        var lngEl = document.getElementById('visitor_longitude');
        var cityEl = document.getElementById('visitor_city');
        var srcEl = document.getElementById('visitor_location_source');

        if (latEl) latEl.value = lat;
        if (lngEl) lngEl.value = lng;
        if (srcEl) srcEl.value = source;
        if (cityEl && city) cityEl.value = city;
        this._locSource = source;
    },

    _reverseGeocode: function (lat, lng, source) {
        var self = this;
        fetch(
            'https://nominatim.openstreetmap.org/reverse?format=json&lat=' +
            lat + '&lon=' + lng,
            { headers: { 'Accept-Language': 'en' } }
        )
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data || !data.address) return;
            var a = data.address;
            var city = a.city || a.town || a.village || a.suburb || a.county || '';
            self._setLocation(lat, lng, source, city);
        })
        .catch(function () { /* silent */ });
    },

    // ── Layer 1: IP geolocation (silent, always runs) ─────────────────

    _tryIpGeolocation: function () {
        var self = this;
        fetch('https://ipapi.co/json/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.latitude && data.longitude) {
                    var city = data.city || data.region || '';
                    self._setLocation(data.latitude, data.longitude, 'ip', city);
                }
            })
            .catch(function () { /* silent */ });
    },

    // ── Layer 2: Network/WiFi positioning (fast, no prompt) ──────────

    _tryNetworkPosition: function () {
        var self = this;
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition(
            function (pos) {
                self._reverseGeocode(pos.coords.latitude, pos.coords.longitude, 'network');
            },
            function () { /* unavailable or denied — silent */ },
            { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }
        );
    },

    // ── Layer 3: High-accuracy GPS (user prompted via banner) ─────────

    _tryGpsBanner: function () {
        var self = this;
        if (!navigator.geolocation) return;

        var banner = document.createElement('div');
        banner.id = 'blx-geo-banner';
        banner.innerHTML =
            '<span style="flex:1;">&#128205; Allow location for better delivery experience.</span>' +
            '<button type="button" id="blx-geo-allow" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:4px 14px;font-size:.8rem;cursor:pointer;white-space:nowrap;">Allow</button>' +
            '<button type="button" id="blx-geo-dismiss" style="background:transparent;border:none;color:#6b7280;font-size:1rem;cursor:pointer;line-height:1;padding:0 4px;">&#10005;</button>';
        banner.style.cssText = 'display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:.83rem;color:#1e40af;';

        var form = document.querySelector('.oe_signup_form_mobile');
        if (form) form.insertBefore(banner, form.firstChild);

        document.getElementById('blx-geo-allow').addEventListener('click', function () {
            banner.innerHTML = '<span style="flex:1;color:#6b7280;">&#8987; Getting precise location…</span>';
            navigator.geolocation.getCurrentPosition(
                function (pos) {
                    banner.innerHTML = '&#9989; Location captured — thank you!';
                    banner.style.cssText = banner.style.cssText
                        .replace('#eff6ff', '#f0fdf4')
                        .replace('#bfdbfe', '#bbf7d0')
                        .replace('#1e40af', '#166534');
                    setTimeout(function () {
                        if (banner.parentNode) banner.parentNode.removeChild(banner);
                    }, 2500);
                    self._reverseGeocode(pos.coords.latitude, pos.coords.longitude, 'gps');
                },
                function () {
                    banner.innerHTML = '<span style="color:#dc2626;">&#9888; Location access denied. Using approximate location.</span>';
                    setTimeout(function () {
                        if (banner.parentNode) banner.parentNode.removeChild(banner);
                    }, 3000);
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        });

        document.getElementById('blx-geo-dismiss').addEventListener('click', function () {
            if (banner.parentNode) banner.parentNode.removeChild(banner);
        });
    },

    // ── Orchestrate all layers ────────────────────────────────────────

    _captureLocation: function () {
        // Layer 1: IP — silent, immediate, always works
        this._tryIpGeolocation();
        // Layer 2: Network/WiFi — fast positioning, no prompt
        this._tryNetworkPosition();
        // Layer 3: GPS banner — highest accuracy, user must allow
        this._tryGpsBanner();
    },

    // ── Contact preference highlight ─────────────────────────────────

    _bindContactPrefHighlight: function () {
        document.querySelectorAll('.contact-pref-option input').forEach(function (input) {
            input.addEventListener('change', function () {
                document.querySelectorAll('.contact-pref-option').forEach(function (lbl) {
                    lbl.style.borderColor = '#d1d5db';
                    lbl.style.background = '';
                });
                if (input.checked || input.type === 'checkbox') {
                    input.closest('.contact-pref-option').style.borderColor = '#2563eb';
                    input.closest('.contact-pref-option').style.background = '#eff6ff';
                }
            });
        });
    },
});
