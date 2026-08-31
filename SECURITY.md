# Security Policy

EDGPT must never ship with API keys, GitHub tokens, tunnel credentials, or a user's runtime `data/` directory.

Credentials entered through EDGPT are stored locally with Windows DPAPI encryption.

Never post tokens, keys, `*.bin` secret files, or unredacted private logs in a public issue.

## GitHub Relay privacy

GitHub Relay can upload detailed Elite Dangerous state and historical journal data, including location/activity history. Use a private state repository unless you intentionally want that information public.

## Reporting a security issue

Do not publish exploitable security issues or credentials in a public issue. Contact the maintainer privately through an appropriate GitHub contact channel first.
