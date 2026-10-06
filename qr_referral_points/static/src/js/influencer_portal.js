/** @odoo-module **/

function getReferralQrImage() {
    return document.getElementById("referral_qr_img");
}

function showCopyFeedback() {
    const feedback = document.getElementById("copy_feedback");
    if (!feedback) {
        return;
    }
    feedback.classList.remove("d-none");
    window.setTimeout(() => feedback.classList.add("d-none"), 1800);
}

async function copyText(text) {
    if (!text) {
        return false;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
    }
    const temp = document.createElement("textarea");
    temp.value = text;
    temp.style.position = "fixed";
    temp.style.opacity = "0";
    document.body.appendChild(temp);
    temp.focus();
    temp.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(temp);
    return ok;
}

async function copyReferralLink(tiktokOnly = false) {
    const input = document.getElementById("referral_link_input");
    const link = input ? input.value : "";
    if (!link) {
        alert("Referral link is not available.");
        return;
    }
    try {
        const ok = await copyText(link);
        if (!ok) {
            throw new Error("copy-failed");
        }
        showCopyFeedback();
        if (tiktokOnly) {
            alert("Referral link copied. Paste it in your TikTok bio.");
        }
    } catch (_err) {
        alert("Could not copy link. Please copy it manually.");
    }
}

function downloadQRCode() {
    const qrImg = getReferralQrImage();
    if (!qrImg || !qrImg.src) {
        alert("QR code is not available.");
        return;
    }
    const link = document.createElement("a");
    link.href = qrImg.src;
    link.download = "referral_qr_code.png";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function printQRCode() {
    const qrImg = getReferralQrImage();
    if (!qrImg || !qrImg.src) {
        alert("QR code is not available.");
        return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
        alert("Please allow popups to print the QR code.");
        return;
    }
    const html = `
        <html>
            <head><title>Print QR Code</title></head>
            <body style="text-align:center;padding-top:20px;">
                <img src="${qrImg.src}" style="max-width:320px;width:100%;" />
            </body>
        </html>
    `;
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onload = function () {
        printWindow.print();
        printWindow.close();
    };
}

function bindInfluencerPortalActions() {
    const copyBtn = document.getElementById("copy_referral_btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => copyReferralLink(false));
    }

    const copyTiktokBtn = document.getElementById("copy_tiktok_btn");
    if (copyTiktokBtn) {
        copyTiktokBtn.addEventListener("click", () => copyReferralLink(true));
    }

    const downloadBtn = document.getElementById("download_qr_btn");
    if (downloadBtn) {
        downloadBtn.addEventListener("click", downloadQRCode);
    }

    const printBtn = document.getElementById("print_qr_btn");
    if (printBtn) {
        printBtn.addEventListener("click", printQRCode);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindInfluencerPortalActions);
} else {
    bindInfluencerPortalActions();
}

// Backward compatibility if cached HTML still has inline onclick attributes.
window.copyReferralLink = copyReferralLink;
window.downloadQRCode = downloadQRCode;
window.printQRCode = printQRCode;

// ── Sales Stage Filter (no page reload) ──────────────────
function blxFilterSales(stage, btn) {
    // Update pill active states
    document.querySelectorAll('.blx-sales-pill').forEach(function (b) {
        var s = b.dataset.stage;
        b.classList.remove('btn-dark', 'btn-primary', 'btn-success', 'active');
        b.style.background = '';
        b.style.color = b.dataset.origColor || '';
    });
    if (btn) {
        btn.style.background = _stageColor(stage);
        btn.style.color = '#fff';
        btn.style.borderColor = _stageColor(stage);
    }

    // Filter order rows
    var rows = document.querySelectorAll('tr[data-order-stage]');
    rows.forEach(function (row) {
        row.style.display = (!stage || row.dataset.orderStage === stage) ? '' : 'none';
    });

    // Hide month sections that have no visible rows
    document.querySelectorAll('.blx-month-section').forEach(function (section) {
        var visible = section.querySelectorAll('tr[data-order-stage]');
        var anyVisible = Array.prototype.some.call(visible, function (r) {
            return r.style.display !== 'none';
        });
        section.style.display = anyVisible ? '' : 'none';
    });
}

function _stageColor(stage) {
    var map = { ordered: '#0d6efd', dispatched: '#fd7e14', delivered: '#6610f2', invoiced: '#0dcaf0', paid: '#198754' };
    return map[stage] || '#343a40';
}
window.blxFilterSales = blxFilterSales;

// ── BLX Tab Switcher ──────────────────────────────────────
function blxTab(panelId, btn) {
    document.querySelectorAll('#blx-tab-container .blx-panel').forEach(function (p) {
        p.style.display = 'none';
    });
    document.querySelectorAll('.blx-portal-tab').forEach(function (b) {
        b.removeAttribute('data-active');
        b.classList.remove('blx-tab-active');
    });
    var panel = document.getElementById(panelId);
    if (panel) { panel.style.display = ''; }
    if (btn) {
        btn.setAttribute('data-active', 'true');
        btn.classList.add('blx-tab-active');
    }
}
window.blxTab = blxTab;

document.addEventListener('DOMContentLoaded', function () {
    // Activate the tab button that has data-active="true" on page load
    var activeBtn = document.querySelector('.blx-portal-tab[data-active="true"]');
    if (activeBtn) {
        var match = activeBtn.getAttribute('onclick').match(/blxTab\('([^']+)'/);
        if (match) { blxTab(match[1], activeBtn); }
    }

    // ── Browser GPS geolocation capture ──────────────────
    if (!navigator.geolocation) return;
    // Only capture once per session (localStorage flag)
    if (localStorage.getItem('blx_geo_sent')) return;

    navigator.geolocation.getCurrentPosition(
        function (pos) {
            localStorage.setItem('blx_geo_sent', '1');
            fetch('/referral/location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                        accuracy: pos.coords.accuracy,
                    },
                }),
            }).catch(function () { /* silent fail */ });
        },
        function () { /* user denied or unavailable — skip silently */ },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    );
});
