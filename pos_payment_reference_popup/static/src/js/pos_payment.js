import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.payment_ref_no = vals.payment_ref_no || "";
    },

    setPaymentReference(reference) {
        this.update({ payment_ref_no: reference || false });
    },

    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            payment_ref_no: this.payment_ref_no,
        };
    },
});
