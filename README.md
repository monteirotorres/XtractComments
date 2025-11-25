
Below is the **updated fully polished README.md** for your project  **XtractComments** , keeping the ASCII logo, sample output, and a *few* emojis as requested.

---

# README.md

**XtractComments**

*Author: Pedro Torres*

```
                                                                                              
 ▄    ▄   ▄                           ▄      ▄▄▄                                       ▄      
  █  █  ▄▄█▄▄   ▄ ▄▄   ▄▄▄    ▄▄▄   ▄▄█▄▄  ▄▀   ▀  ▄▄▄   ▄▄▄▄▄  ▄▄▄▄▄   ▄▄▄   ▄ ▄▄   ▄▄█▄▄   ▄▄▄  
   ██     █     █▀  ▀ ▀   █  █▀  ▀    █    █      █▀ ▀█  █ █ █  █ █ █  █▀  █  █▀  █    █    █   ▀ 
  ▄▀▀▄    █     █     ▄▀▀▀█  █        █    █      █   █  █ █ █  █ █ █  █▀▀▀▀  █   █    █     ▀▀▀▄ 
 ▄▀  ▀▄   ▀▄▄   █     ▀▄▄▀█  ▀█▄▄▀    ▀▄▄   ▀▄▄▄▀ ▀█▄█▀  █ █ █  █ █ █  ▀█▄▄▀  █   █    ▀▄▄  ▀▄▄▄▀ 
                                                                                              
                                                                                                
```

📝 **A precision tool for extracting clean, journal-ready annotation reports from PDFs — ideal for manuscript peer review.**

---

## ✨ Overview

**XtractComments** scans annotated PDF manuscripts and generates a structured **TXT report** containing:

* Page numbers
* Accurate line numbers
* Highlighted text (normalized, ellipsis-wrapped, newline-free)
* Reviewer comments
* Strikeout-based substitution suggestions

It is designed for researchers, editors, and reviewers who need a fast and reliable way to convert handwritten manuscript annotations into a clean, submission-ready list of comments.

---

## 🚀 Features

### **1. Printed Line Number Detection (Primary Mode)**

If the manuscript contains **printed line numbers** (common in journal submissions), XtractComments:

* Detects the line numbers directly from the PDF margin
* Ignores header regions
* Maps each annotation to the nearest printed line number
* Produces *exact* line references (no drift)

### **2. Intelligent Fallback Mode**

If a page lacks printed numbers:

* Reconstructs text "body lines" from PDF structure
* Skips the header region
* Assigns each annotation to the closest textual line
* Guarantees line mapping even in format-poor PDFs

### **3. Clean Editorial Formatting**

Output uses a manuscript-friendly structure:

```
Page X, line Y, ...highlighted text...: comment
Page X, line Y: substitute "...old text..." for "new text"
```

Strikeout annotations become “substitute” instructions.

### **4. Highlight Normalization**

* Removes newlines
* Collapses multiple spaces
* Wraps with ellipsis (`...text...`)
* Strips quotes safely

✔ Ensures ready-to-paste content for peer-review systems (e.g., ScholarOne, Editorial Manager).

---

## 📦 Installation

Requires Python 3.8+ and PyMuPDF:

```bash
pip install pymupdf
```

Run the script:

```bash
python extract_pdf_annotations_txt.py manuscript.pdf
```

---

## 🧪 Sample Output

```
Comments to the Author

Page 2, line 19, ...the catalytic mechanism requires further clarification...: unclear phrasing
Page 4, line 28: substitute "...protein dimer..." for "homodimer"
Page 7, line 12, ...these constraints should be justified...: please elaborate
Page 10, line 4, ...significantly improves accuracy...: maybe quantify this?
```

---

## 🧰 Command Line Options

| Argument               | Purpose                                                                     | Default  |
| ---------------------- | --------------------------------------------------------------------------- | -------- |
| `--header-margin-cm` | Region above this height is treated as header                               | `1.5`  |
| `--margin-frac`      | Fraction of page width treated as margin for detecting printed line numbers | `0.15` |

Run with custom output:

```bash
python extract_pdf_annotations_txt.py manuscript.pdf -o comments.txt
```

---

## 📁 Example Repository Layout

```
XtractComments/
│
├── extract_pdf_annotations_txt.py
├── README.md
└── sample/
    ├── example.pdf
    └── example_output.txt
```

Where `example_output.txt` contains sample results similar to the snippet above.

---

## 🔧 Known Limitations

* Very complex layouts (e.g., math-heavy papers) may require manual verification.
* Journals printing line numbers on the **right margin** require adjusting the detection rule (can be added on request).
* Some vectorized or image-based PDFs may fail to extract text properly (limitations of the PDF itself).

---

## 🙌 Contributing

Pull requests and suggestions are welcome.

Potential improvements:

* Automatic right-margin detection
* Debug mode for visualizing printed line number detection
* JSON or Markdown output formats

---

## 📜 License

MIT License — free for personal, academic, and editorial use.
