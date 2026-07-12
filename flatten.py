"""Flatten a multi-file LaTeX project into one .tex file.

Usage: python flatten.py <main.tex> <result.tex>
"""
import os
import re
import sys

# \input{f} or \include{f}
CMD = re.compile(r"\\(?:input|include)\s*\{([^}]*)\}")
# \includegraphics[...]{...} -- lines with one get commented out (images dropped)
GRAPHICS = re.compile(r"\\includegraphics\b")
# \bibliography{a,b} -- names of the .bib files this document cites
BIB = re.compile(r"\\bibliography\s*\{([^}]*)\}")


def code_part(line):
    """Split a line into (code, comment) at the first unescaped '%'."""
    i = 0
    while True:
        j = line.find("%", i)
        if j == -1:
            return line, ""
        if j == 0 or line[j - 1] != "\\":
            return line[:j], line[j:]
        i = j + 1


def resolve(target, root_dir):
    """Resolve an \\input/\\include target relative to the MAIN doc dir."""
    p = target if os.path.splitext(target)[1] else target + ".tex"
    return os.path.normpath(os.path.join(root_dir, p))


def resolve_bib(name, root_dir):
    """Resolve a \\bibliography entry to a .bib path, relative to the main dir."""
    p = name if name.lower().endswith(".bib") else name + ".bib"
    return os.path.normpath(os.path.join(root_dir, p))


def expand(path, root_dir, out, in_progress, bibs=None):
    real = os.path.normpath(os.path.abspath(path))
    if real in in_progress:
        raise RuntimeError(f"include cycle at {real}")
    in_progress.add(real)
    with open(real, encoding="utf-8") as f:
        for line in f:
            code, comment = code_part(line)
            if bibs is not None:
                for m in BIB.finditer(code):
                    bibs.update(n.strip() for n in m.group(1).split(",") if n.strip())
            if GRAPHICS.search(code):  # comment out image lines, don't expand them
                out.write(line if line.lstrip().startswith("%") else "% " + line)
                continue
            if not CMD.search(code):
                out.write(code + comment)
                continue
            pos = 0
            for m in CMD.finditer(code):
                out.write(code[pos:m.start()])
                expand(resolve(m.group(1), root_dir), root_dir, out, in_progress, bibs)
                out.write("\n")  # ensure files never glue together (req #3)
                pos = m.end()
            out.write(code[pos:] + comment)
    in_progress.discard(real)


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(
        prog="flatten.py",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Flatten a multi-file LaTeX project into a single .tex file.\n\n"
            "Recursively inlines every \\input and \\include (paths resolved\n"
            "relative to the main document's directory). Lines containing\n"
            "\\includegraphics are commented out rather than deleted. Comments\n"
            "and everything else are copied verbatim."
        ),
        epilog=(
            "Examples:\n"
            "  python flatten.py main.tex out.tex   # write to out.tex\n"
            "  python flatten.py main.tex           # write to ./result.tex"
        ),
    )
    ap.add_argument("-h", action="help", help="show this help message and exit")
    ap.add_argument("main_tex", help="root document (the one with \\begin{document})")
    ap.add_argument(
        "result_tex",
        nargs="?",
        help="output path (overwritten). Default: ./result.tex in the current directory",
    )
    ap.add_argument(
        "-b",
        action="store_true",
        help="also copy the cited .bib file(s) next to the result file",
    )
    a = ap.parse_args(argv)
    result = a.result_tex or os.path.join(os.getcwd(), "result.tex")
    root_dir = os.path.dirname(os.path.abspath(a.main_tex))
    bibs = set() if a.b else None
    with open(result, "w", encoding="utf-8") as out:
        expand(a.main_tex, root_dir, out, set(), bibs)
    print(f"wrote {result}")
    if bibs:
        import shutil

        dest_dir = os.path.dirname(os.path.abspath(result))
        for name in sorted(bibs):
            src = resolve_bib(name, root_dir)
            dst = os.path.join(dest_dir, os.path.basename(src))
            if os.path.abspath(src) == os.path.abspath(dst):
                continue  # already there
            shutil.copyfile(src, dst)
            print(f"copied {dst}")


def _selfcheck():
    import io
    import tempfile

    d = tempfile.mkdtemp()
    with open(os.path.join(d, "main.tex"), "w", encoding="utf-8") as f:
        f.write("A\n\\input{sub}\nB\n% \\input{ignored}\n")
    with open(os.path.join(d, "sub.tex"), "w", encoding="utf-8") as f:
        f.write("X\n\\includegraphics[width=1cm]{p.png}\nY")  # no trailing newline
    out = io.StringIO()
    expand(os.path.join(d, "main.tex"), d, out, set())
    r = out.getvalue()
    assert "A" in r and "B" in r and "X" in r and "Y" in r, r
    assert "\\input{sub}" not in r, r  # real command was expanded
    assert "% \\includegraphics[width=1cm]{p.png}" in r, r  # image line commented out
    assert "\n\\includegraphics" not in r, r  # no active (uncommented) image left
    assert "% \\input{ignored}" in r, r  # commented command kept verbatim, not expanded
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selfcheck":
        _selfcheck()
    else:
        main()
