# Kubernetes PDF Documentation

### This repository contains all the [Kubernetes documentation](https://kubernetes.io/docs/home/) in PDF format.

## How the files are structured?
PDF files can be found under PDFs directory. Each PDF is a section in the site.

* Documentation (ignored)
* Getting started - Setup.pdf
* Concepts - Concepts.pdf
* Tasks - Tasks.pdf
* Tutorials - Tutorials.pdf
* Reference - Reference.pdf
* Contribute - Contrubute.pdf

## Dependencies
* docker (Docker UI)
* requests-html
* lxml_html_clean

# How to run the code
1. Clone the repository.
2. Create the virtual environment. `myenv` is the name of the environment.
```shell
python3 -m venv myenv                                                                                                                                                ✔
source myenv/bin/activate
```
3. Run Docker UI
4. Install dependencies
```shell
pip install requests-html
pip install lxml_html_clean
```
5. Run `kubernetes-doc.py`
```shell
python kubernetes-doc.py
```

# Similar Project:

* [Terraform PDF Documentation](https://github.com/dohsimpson/terraform-doc-pdf)
