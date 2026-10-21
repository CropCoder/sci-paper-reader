# Contributing

Thanks for considering a contribution to **Sci Paper Reader**.

## Ways to contribute

- Report a bug with a minimal PDF or a description of the failing layout.
- Suggest a feature: new page type, new output, better figure handling, more languages.
- Improve the writing rules in `references/` (translation, figures, methods, WeChat, talk).
- Improve the HTML/CSS templates in `templates/`.
- Add a test fixture for a paper layout that currently fails.

## Development setup

```bash
git clone https://github.com/CropCoder/sci-paper-reader.git
cd sci-paper-reader
python3 -m pip install -r requirements.txt
make test
make check
```

## Pull requests

1. Keep changes focused; one topic per PR.
2. Update `references/` or `SKILL.md` if you change the agent contract.
3. Add or update a test fixture when fixing extraction or builder behavior.
4. Run `make test` and `make check` before opening the PR.
5. Do not commit generated paper bundles, PDFs, or `__pycache__`.

## Commit messages

Use conventional-style prefixes where possible:

- `feat:` new capability
- `fix:` bug fix
- `docs:` documentation or writing rules
- `test:` tests or fixtures
- `chore:` maintenance

## Reporting layout bugs

A PDF is often copyrighted. Prefer a description of the layout (single/two-column, vector/raster
figures, caption above/below) plus a screenshot of the failing crop. Do not upload a full paper unless
you have the right to share it.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
