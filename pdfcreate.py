from fpdf import FPDF
import json
import textwrap
import os
import re

class PDFGenerator:
    def __init__(self):
        # Create output directory if it doesn't exist
        self.output_dir = "generated_pdfs"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def clean_text(self, text):
        """Clean text to avoid encoding issues"""
        if not isinstance(text, str):
            text = str(text)
        # Replace problematic characters
        text = text.replace('²', '2')
        text = text.replace('→', '->')
        text = text.replace('•', '-')  # Fix bullet point issue
        # Remove any other problematic characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        return text.strip()

    def create_main_content_pdf(self, content):
        """Creates PDF for main educational content"""
        try:
            if not content:
                print("No main content provided")
                return False

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)  # Prevent text cutoff
            pdf.add_page()

            # Ensure the font supports UTF-8
            pdf.set_font('Arial', '', 12)

            # Content processing
            lines = content.split('\n')
            in_bullet_list = False

            for line in lines:
                line = self.clean_text(line)

                if not line:
                    if in_bullet_list:
                        in_bullet_list = False
                    pdf.ln(5)
                    continue

                # Handle section titles (bold text with **)
                if line.startswith('**') and line.endswith('**'):
                    if in_bullet_list:
                        in_bullet_list = False
                        pdf.ln(5)
                    pdf.set_font('Arial', 'B', 14)
                    title_text = line.strip('*')
                    pdf.multi_cell(0, 10, title_text, align='L')
                    pdf.ln(5)

                # Handle bullet points
                elif line.strip().startswith('*'):
                    pdf.set_font('Arial', '', 12)
                    in_bullet_list = True
                    bullet_text = line.strip('* ').strip()
                    pdf.set_x(20)  # Indent bullet points
                    pdf.multi_cell(0, 10, f"- {bullet_text}", align='L')

                # Regular text
                else:
                    if in_bullet_list:
                        in_bullet_list = False
                        pdf.ln(5)
                    pdf.set_font('Arial', '', 12)
                    pdf.multi_cell(0, 10, line, align='L')
                    pdf.ln(5)

            output_path = os.path.join(self.output_dir, 'main_content.pdf')
            pdf.output(output_path, "F")  # Ensure UTF-8 encoding
            print(f"Successfully created main content PDF at {output_path}")
            return True

        except Exception as e:
            print(f"Error creating main content PDF: {str(e)}")
            return False

    def extract_mcq_questions(self, data):
        """Extract and validate MCQ questions from data"""
        return [item for item in data if isinstance(item, dict) and 'question' in item and 'options' in item and 'scenario' not in item]

    def create_mcq_pdf(self, mcq_data):
        """Creates PDF for multiple choice questions"""
        try:
            mcq_questions = self.extract_mcq_questions(mcq_data)
            if not mcq_questions:
                print("No valid MCQ questions found")
                return False

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Multiple Choice Questions', ln=True, align='C')
            pdf.ln(10)

            for i, mcq in enumerate(mcq_questions, 1):
                try:
                    pdf.set_font('Arial', 'B', 12)
                    question = self.clean_text(mcq.get('question', 'No question provided'))
                    pdf.multi_cell(0, 10, f"{i}. {question}")
                    pdf.ln(5)

                    pdf.set_font('Arial', '', 12)
                    for j, option in enumerate(mcq.get('options', []), 1):
                        pdf.multi_cell(0, 10, f"    {chr(96+j)}) {self.clean_text(option)}")

                    pdf.ln(5)
                    pdf.set_font('Arial', 'B', 12)
                    pdf.multi_cell(0, 10, f"Correct Answer: {self.clean_text(mcq.get('correct_answer', 'Not provided'))}")

                    pdf.set_font('Arial', 'I', 12)
                    pdf.multi_cell(0, 10, f"Explanation: {self.clean_text(mcq.get('explanation', 'No explanation provided'))}")
                    pdf.ln(10)

                except Exception as e:
                    print(f"Error processing question {i}: {str(e)}")
                    continue

            output_path = os.path.join(self.output_dir, 'mcq_questions.pdf')
            pdf.output(output_path)
            print(f"Successfully created MCQ PDF at {output_path}")
            return True

        except Exception as e:
            print(f"Error creating MCQ PDF: {str(e)}")
            return False

    def extract_case_studies(self, data):
        """Extract case studies from data"""
        return [item for item in data if isinstance(item, dict) and 'scenario' in item]

    def create_case_studies_pdf(self, case_data):
        """Creates PDF for case studies"""
        try:
            case_studies = self.extract_case_studies(case_data)
            if not case_studies:
                print("No valid case studies found")
                return False

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Case Studies', ln=True, align='C')
            pdf.ln(10)

            for i, case in enumerate(case_studies, 1):
                pdf.set_font('Arial', 'B', 14)
                pdf.multi_cell(0, 10, f"Case Study {i}")
                pdf.ln(5)

                pdf.set_font('Arial', 'B', 12)
                pdf.multi_cell(0, 10, "Scenario:")
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(0, 10, self.clean_text(case.get('scenario', 'No scenario provided')))
                pdf.ln(5)

                pdf.set_font('Arial', 'B', 12)
                pdf.multi_cell(0, 10, "Question:")
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(0, 10, self.clean_text(case.get('question', 'No question provided')))
                pdf.ln(5)

                pdf.set_font('Arial', 'B', 12)
                pdf.multi_cell(0, 10, "Answer:")
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(0, 10, self.clean_text(case.get('answer', 'No answer provided')))
                pdf.ln(10)

            output_path = os.path.join(self.output_dir, 'case_studies.pdf')
            pdf.output(output_path)
            print(f"Successfully created case studies PDF at {output_path}")
            return True

        except Exception as e:
            print(f"Error creating case studies PDF: {str(e)}")
            return False

def main():
    data = json.load(open("data.json"))  # Load data from a JSON file
    pdf_gen = PDFGenerator()
    pdf_gen.create_main_content_pdf(data['main_content'])
    pdf_gen.create_mcq_pdf(data['mcq_questions'])
    pdf_gen.create_case_studies_pdf(data['case_studies'])

if __name__ == "__main__":
    main()
