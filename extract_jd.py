from docx import Document

doc = Document("docs/job_description.docx")
text = "\n".join(p.text for p in doc.paragraphs)

with open("jd_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(f"Wrote {len(text)} characters")