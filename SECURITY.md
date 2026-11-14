# Security Policy

## Supported versions

Only the latest release (and `main`) receives fixes.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Report it privately through GitHub:
*Security ▸ Report a vulnerability* on <https://github.com/alexandrevl/tiny-desk-radio/security/advisories/new>.

Include what you found, how to reproduce it, and the version or commit. You will get an answer within about
a week; this is a volunteer project, so please be patient. Once a fix is released the report may be
published with credit to you, unless you prefer otherwise.

## Scope notes

`tinydesk` runs locally and processes untrusted text (video titles and descriptions) and media downloaded
by `yt-dlp` through `ffmpeg`. Reports about path handling for file names derived from titles, regular
expressions that can hang on crafted input, unsafe handling of downloaded files, or the model download are
in scope. Vulnerabilities in `yt-dlp`, `ffmpeg`, Whisper or other dependencies should be reported to those
projects.
