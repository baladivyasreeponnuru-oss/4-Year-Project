from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors


def generate_question_paper_pdf(header, part_a_questions, part_b_questions, output_path):
    styles = getSampleStyleSheet()

    code_style = ParagraphStyle('Code', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold')
    college_style = ParagraphStyle('College', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#1a1a6e'))
    department_style = ParagraphStyle('Department', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold')
    exam_title_style = ParagraphStyle('ExamTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11)
    subject_style = ParagraphStyle('Subject', parent=styles['Normal'], alignment=TA_CENTER, fontSize=13, fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4)
    common_style = ParagraphStyle('Common', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, fontName='Helvetica-Bold')
    time_marks_style = ParagraphStyle('TimeMarks', parent=styles['Normal'], fontSize=10.5, fontName='Helvetica-Bold')
    part_heading_style = ParagraphStyle('PartHeading', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=2)
    part_sub_style = ParagraphStyle('PartSub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=8)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=10, leading=13.5)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER)
    marks_style = ParagraphStyle('Marks', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER)
    or_style = ParagraphStyle('Or', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')

    story = []
    story.append(Paragraph(f"CODE: {header.get('code', 'XXXXXXX')}", code_style))
    story.append(Spacer(1, 4))
    if header.get('college_name'):
        story.append(Paragraph(header['college_name'], college_style))
    if header.get('department'):
        story.append(Paragraph(header['department'], department_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(header.get('exam_title', ''), exam_title_style))
    story.append(Paragraph(header.get('subject_name', 'SUBJECT NAME'), subject_style))

   
    if header.get('common_for'):
        story.append(Paragraph(f"({header['common_for']})", common_style))
    story.append(Spacer(1, 8))

    time_marks_table = Table(
        [[Paragraph(f"Time: {header.get('time_duration', '3 hours')}", time_marks_style),
          Paragraph(f"Max. Marks: {header.get('max_marks', 100)}", time_marks_style)]],
        colWidths=[3.2 * inch, 3.2 * inch]
    )
    time_marks_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(time_marks_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("PART &ndash; A", part_heading_style))
    story.append(Paragraph("(Compulsory Question)", part_sub_style))

    if not part_a_questions:
        story.append(Paragraph("No Part A questions were available for this pattern.", cell_style))
        story.append(Spacer(1, 14))
    else:
        total_a_marks = sum(q['marks'] for q in part_a_questions)
        part_a_data = [[
            Paragraph("1", label_style),
            Paragraph(f"Answer the following: (5 X {part_a_questions[0]['marks']:02d} = {total_a_marks} Marks)", cell_style),
            ""
        ]]
        sub_labels = ['(a)', '(b)', '(c)', '(d)', '(e)']
        for i, q in enumerate(part_a_questions):
            co_tag = f" (CO{q['co']}, K{q.get('k', 2)})" if q.get('co') else ""
            part_a_data.append([
                Paragraph(sub_labels[i] if i < len(sub_labels) else f"({i+1})", label_style),
                Paragraph(f"{q['question']}{co_tag}", cell_style),
                Paragraph(f"{q['marks']}M", marks_style)
            ])

        part_a_table = Table(part_a_data, colWidths=[0.5 * inch, 5.2 * inch, 0.7 * inch])
        part_a_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (1, 0), (2, 0)),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(part_a_table)
    story.append(Spacer(1, 14))

    total_b_marks = sum(q['marks'] for q in part_b_questions) if part_b_questions else 0
    story.append(Paragraph("PART &ndash; B", part_heading_style))
    if part_b_questions:
        story.append(Paragraph(f"(Answer all the questions: 05 X {part_b_questions[0]['marks']:02d} = {total_b_marks} Marks)", part_sub_style))
    else:
        story.append(Paragraph("No Part B questions were available for this pattern.", cell_style))


    part_b_data = []
    for i, q in enumerate(part_b_questions, 1):
        co_tag = f" (CO{q['co']}, K{q.get('k', 3)})" if q.get('co') else ""
        part_b_data.append([
            Paragraph(str(i), label_style),
            Paragraph(f"{q['question']}{co_tag}", cell_style),
            Paragraph(f"{q['marks']}M", marks_style)
        ])
        if q.get('alt'):
            part_b_data.append([
                Paragraph("", label_style),
                Paragraph("OR", or_style),
                Paragraph("", marks_style)
            ])
            alt = q['alt']
            alt_co_tag = f" (CO{alt['co']}, K{alt.get('k', 3)})" if alt.get('co') else ""
            part_b_data.append([
                Paragraph("", label_style),
                Paragraph(f"{alt['question']}{alt_co_tag}", cell_style),
                Paragraph(f"{alt['marks']}M", marks_style)
            ])

    if part_b_data:
        part_b_table = Table(part_b_data, colWidths=[0.5 * inch, 5.2 * inch, 0.7 * inch])
        part_b_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(part_b_table)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    doc.build(story)
    return output_path