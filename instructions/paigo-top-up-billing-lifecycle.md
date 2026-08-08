<uploaded_files>/app</uploaded_files>

# Add prepaid-credit top-up billing

Usage-based offerings need a `"topUp"` billing cycle backed by the existing customer wallet. The create and read contracts use string fields `topUpAmount` and optional `topUpThreshold`; the threshold defaults to `"0.2"`. A top-up amount is required for this billing cycle, top-up fields are invalid on other cycles, and subscription offerings cannot use it. Persist and return these fields without changing existing offering behavior.

Create one hourly scheduler per top-up offering. Enrollment and every hourly check must refill a wallet only when its balance is below `topUpThreshold * topUpAmount`, charging exactly the gap to `topUpAmount` through an invoice whose payment is stored as credit. Hourly usage must be deducted as a wallet transaction even when it exceeds the current balance; it must not generate a separate usage invoice. After the deduction, evaluate the refill using the updated balance. Preserve normal monthly and annual billing, invoice payment, and credit behavior.

Verify with:

    cd /app && npm run build && npm run test:ci -- --runInBand
