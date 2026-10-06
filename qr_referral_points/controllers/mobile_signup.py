# mobile_signup.py — DISABLED
# All mobile signup routes have moved to signup_with_dibon_sms.
# The combined flow is:
#   /mobile/signup        → Step 1: mobile (required) + email (optional)
#   /mobile/signup/send-otp → POST: validate, generate OTP, send via sms.sms
#   /mobile/signup/verify → Step 2: enter OTP
#   /web/signup-mobile    → Step 3: full details form (name, town, password, comm mode)
