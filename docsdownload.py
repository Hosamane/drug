from flask import Flask, render_template, send_file
import sqlite3
from fpdf import FPDF
import os

app = Flask(__name__)

DB_PATH = "instance/history.db"
PDF_PATH = "history_output.pdf"

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, "Patient History Report", border=False, ln=True, align='C')
        self.ln(5)

    def table_header(self, headers):
        self.set_font("Arial", 'B', 12)
        for header in headers:
            self.cell(38, 10, header, border=1)
        self.ln()

    def table_row(self, row):
        self.set_font("Arial", '', 10)
        for col in row:
            self.cell(38, 10, str(col), border=1)
        self.ln()

# def generate_pdf():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     cursor.execute("SELECT `id`, `user_id`, `symptoms`, `predicted_disease`, `timestamp` FROM `symptom_history`")  # assuming your table is named 'history'
#     rows = cursor.fetchall()

#     headers = ["ID", "User ID", "Symptoms", "Predicted Disease", "Timestamp"]

#     pdf = PDF()
#     pdf.add_page()
#     pdf.table_header(headers)

#     for row in rows:
#         pdf.table_row(row)

#     pdf.output(PDF_PATH)
#     conn.close()

def generate_pdf():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, user_id, symptoms, predicted_disease, timestamp FROM symptom_history")
    rows = cursor.fetchall()

    headers = ["ID", "User ID", "Symptoms", "Predicted Disease", "Timestamp"]
    col_widths = [15, 25, 60, 50, 40]

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Draw header
    pdf.set_font("Arial", 'B', 12)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    # Set font for data
    pdf.set_font("Arial", '', 10)

    for row in rows:
        # Save current position
        x_start = pdf.get_x()
        y_start = pdf.get_y()

        # First, calculate height required for each cell using MultiCell
        line_heights = []
        for i, text in enumerate(row):
            text = str(text)
            # Simulate multi_cell to calculate height
            text_width = col_widths[i]
            text_lines = pdf.multi_cell(text_width, 5, text, border=0, split_only=True)
            line_heights.append(5 * len(text_lines))

        row_height = max(line_heights)

        # Check if page break is needed
        if y_start + row_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            # Redraw header
            pdf.set_font("Arial", 'B', 12)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, border=1)
            pdf.ln()
            pdf.set_font("Arial", '', 10)
            x_start = pdf.get_x()
            y_start = pdf.get_y()

        # Draw each cell manually
        for i, text in enumerate(row):
            text = str(text)
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(col_widths[i], 5, text, border=1, align='L')
            pdf.set_xy(x + col_widths[i], y)  # move to next column at same line

        pdf.ln(row_height)

    pdf.output(PDF_PATH)
    conn.close()



@app.route('/')
def index():
    return render_template('docs.html')

@app.route('/download', methods=['POST'])
def download():
    generate_pdf()
    return send_file(PDF_PATH, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
