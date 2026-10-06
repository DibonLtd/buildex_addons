import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (
            paymentMethod.type === "pay_later" &&
            (!this.currentOrder.to_invoice ||
                this.pos.models["ir.module.module"].find((m) => m.name === "pos_settle_due")
                    ?.state !== "installed")
        ) {
            this.notification.add(
                _t(
                    "To ensure due balance follow-up, generate an invoice or download the accounting application. "
                ),
                { autocloseDelay: 7000, title: _t("Warning") }
            );
        }
        if (this.pos.paymentTerminalInProgress && paymentMethod.use_payment_terminal) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return false;
        }

        const paymentReference = await this._promptPaymentReference(paymentMethod);
        if (paymentReference === false) {
            return false;
        }

        const newPaymentLine = this.currentOrder.add_paymentline(paymentMethod);
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return false;
        }
        if (!newPaymentLine) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return false;
        }

        newPaymentLine.setPaymentReference(paymentReference);
        this.numberBuffer.reset();

        if (
            paymentMethod.use_payment_terminal &&
            (paymentMethod.payment_terminal?.fast_payments ?? true)
        ) {
            this.sendPaymentRequest(newPaymentLine);
        }
        return true;
    },

    async _promptPaymentReference(paymentMethod) {
        if (!paymentMethod.ask_payment_reference) {
            return "";
        }

        const label = paymentMethod.payment_reference_label || _t("Payment Reference");
        const reference = await makeAwaitable(this.dialog, TextInputPopup, {
            title: label,
            placeholder: label,
            startingValue: "",
        });

        if (reference === undefined) {
            return false;
        }

        const cleanedReference = reference.trim();
        if (paymentMethod.payment_reference_required && !cleanedReference) {
            this.dialog.add(AlertDialog, {
                title: _t("Missing Reference"),
                body: _t("A payment reference is required for this payment method."),
            });
            return false;
        }

        return cleanedReference;
    },
});
