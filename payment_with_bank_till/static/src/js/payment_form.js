/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';
import { _t } from "@web/core/l10n/translation";
import { rpc, RPCError } from "@web/core/network/rpc";

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Bank Till for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'bank_till') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return;
        }
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Send the payment reference to the server then redirect to the status page.
     *
     * @override method from payment.payment_form
     * @private
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'bank_till') {
            this._super(...arguments);
            return;
        }

        const referenceInput = document.getElementById('bank_till_payment_reference');
        const paymentReference = referenceInput ? referenceInput.value.trim() : '';

        if (!paymentReference) {
            this._displayError(
                _t("Payment Reference Required"),
                _t("Please enter your M-PESA confirmation code before submitting.")
            );
            this._enableButton?.();
            return;
        }

        rpc('/payment/bank_till/process', {
            'reference': processingValues.reference,
            'payment_reference': paymentReference,
        }).then(() => {
            window.location = '/payment/status';
        }).catch(error => {
            if (error instanceof RPCError) {
                this._displayError(_t("Payment processing failed"), error.data.message);
                this._enableButton?.();
            } else {
                return Promise.reject(error);
            }
        });
    },

});
