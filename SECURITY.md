# Security Policy

## Supported versions

The latest release on the `main` branch is supported.

## Reporting a vulnerability

Please do not open a public issue for security-sensitive reports. Use GitHub's
[private vulnerability reporting](https://github.com/CropCoder/sci-paper-reader/security/advisories/new)
or contact the maintainer through the GitHub profile.

We will acknowledge a report as soon as possible and coordinate a fix and disclosure.

## Scope

This project is a local skill and build tool. It does not run a server. Relevant issues include:

- unsafe handling of untrusted PDFs or file paths,
- generated HTML containing unescaped content,
- dependency vulnerabilities.

The HTML templates escape extracted text before injecting it into the DOM; keep that property when
changing the builders or page scripts.
