# Latex flat

Flatten a multi-file LaTeX project into a single `.tex` file. Every `\input`
and `\include` is recursively inlined; the result compiles on its own.

## Install

```
pip install latex-flat
```

This installs the `latexflat` command:

```
latexflat <main.tex> [result.tex] [-b]
```

## Usage

Installed command (or run the script directly with `python flatten.py ...`):

```
latexflat <main.tex> [result.tex] [-b]
```

- `<main.tex>` — the root document (the one with `\begin{document}`).
- `[result.tex]` — output path (overwritten). Defaults to `./result.tex`.
- `-b` — also copy the cited `.bib` file(s) next to the result.
- `-h` — show help.

Example:

```
latexflat main.tex out.tex -b
```

## Behaviour

- `\input` / `\include` → inlined (paths resolved relative to the main doc's dir).
- Lines with `\includegraphics` → commented out (images dropped, not deleted).
- Comments and everything else → copied verbatim.
- Include cycles are detected and error out.
