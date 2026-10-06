odoo.define('custom_whatsapp.whatsapp_qr_poll', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;

    var pollInterval = 3000; // 3 seconds
    var pollTimer = null;

    function startPolling(wizardId) {
        function poll() {
            rpc.query({
                model: 'whatsapp.qr.wizard',
                method: 'check_connection',
                args: [[wizardId]],
            }).then(function (result) {
                if (result && result.tag === 'display_notification' && result.params && result.params.type === 'success') {
                    if (pollTimer) {
                        clearTimeout(pollTimer);
                        pollTimer = null;
                    }
                    // Try to close modal and reload page robustly
                    var $modal = $(".modal-dialog").closest('.modal');
                    if ($modal.length) {
                        $modal.modal('hide');
                    }
                    setTimeout(function() {
                        window.location.href = window.location.href;
                    }, 500);
                } else {
                    pollTimer = setTimeout(poll, pollInterval);
                }
            }).catch(function () {
                pollTimer = setTimeout(poll, pollInterval);
            });
        }
        poll();
    }

    // Attach to the QR wizard modal
    core.bus.on('DOM_updated', null, function () {
        var $modal = $(".modal-dialog form.o_form_view");
        if ($modal.length && $modal.find('[name="qr_scan"]').length) {
            var wizardId = $modal.find('input[name="id"]').val() || $modal.find('input[name="res_id"]').val();
            // Always allow polling to restart for new modals
            if (wizardId) {
                window._whatsappQrPollingStarted = false;
                startPolling(parseInt(wizardId));
            }
        }
    });

    return {
        startPolling: startPolling
    };
});
