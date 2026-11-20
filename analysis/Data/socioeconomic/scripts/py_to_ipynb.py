"""Convert a '# %%' percent-format script into a Jupyter notebook: python py_to_ipynb.py src.py out.ipynb"""
import sys, re, nbformat as nbf
src = open(sys.argv[1]).read()
cells = []
for block in re.split(r"^# %%", src, flags=re.M)[1:]:
    head, _, body = block.partition("\n")
    body = body.strip("\n")
    if "[markdown]" in head:
        cells.append(nbf.v4.new_markdown_cell("\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in body.splitlines())))
    elif body:
        cells.append(nbf.v4.new_code_cell(body))
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, sys.argv[2])
