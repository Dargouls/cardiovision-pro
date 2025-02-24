import os
import chardet
import re
from datetime import datetime

class AdvancedMedicalReportExtractor:
    def __init__(self, text):
        self.text = text
        self.cleaned_text = self.clean_text(text)

    def clean_text(self, text):
        """Remove caracteres não-ASCII e espaços extras."""
        # Substitui caracteres não-ASCII por espaço
        cleaned_text = re.sub(r'[^\x00-\x7F]', ' ', text)
        # Remove espaços extras
        return cleaned_text.strip()

    def is_valid_date(self, date_str, date_format):
        """Verifica se a string representa uma data válida e se não é futura."""
        try:
            date = datetime.strptime(date_str, date_format)
            return date < datetime.now()
        except ValueError:
            return False

    def extract_birth_date(self):
        """Extrai a data de nascimento usando múltiplos padrões, inclusive timestamps de 14 dígitos."""
        patterns = [
            (r'\b(\d{14})\b', '%Y%m%d%H%M%S'),
            (r'\b(\d{8})\b', '%d%m%Y'),
            (r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', None),
            (r'\b(\d{4}[/-]\d{2}[/-]\d{2})\b', '%Y-%m-%d'),
            (r'\b(\d{2}-[A-Za-z]{3}-\d{4})\b', '%d-%b-%Y')
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, self.cleaned_text)
            if match:
                date_str = match.group(1)
                local_fmt = fmt
                if local_fmt is None:
                    if '/' in date_str:
                        local_fmt = '%d/%m/%Y'
                    elif '-' in date_str:
                        local_fmt = '%Y-%m-%d' if date_str[:4].isdigit() else '%d-%m-%Y'
                if self.is_valid_date(date_str, local_fmt):
                    dt = datetime.strptime(date_str, local_fmt)
                    return dt.strftime('%d/%m/%Y')

        context_pattern = (
            r'\b(nascimento|nasc\.|nascido|data de nascimento)\b\s*[:-]\s*'
            r'(\d{14}|\d{8}|\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2}|\d{2}-[A-Za-z]{3}-\d{4})'
        )
        context_match = re.search(context_pattern, self.cleaned_text, re.IGNORECASE)
        if context_match:
            date_str = context_match.group(2)
            local_fmt = None
            if len(date_str) == 14:
                local_fmt = '%Y%m%d%H%M%S'
            elif len(date_str) == 8:
                local_fmt = '%d%m%Y'
            elif '/' in date_str:
                local_fmt = '%d/%m/%Y'
            elif '-' in date_str:
                local_fmt = '%Y-%m-%d' if date_str[:4].isdigit() else '%d-%b-%Y'
            if local_fmt and self.is_valid_date(date_str, local_fmt):
                dt = datetime.strptime(date_str, local_fmt)
                return dt.strftime('%d/%m/%Y')
        return 'Não encontrada'
    def extract_doctors(self):
        print(self.text)
        """Extrai os nomes dos médicos do laudo."""
        return re.findall(r'Dr\. (\w+\s+\w+)', self.cleaned_text)

    def extract_patient_names(self):
        """Extrai os nomes dos pacientes do laudo."""
        return re.findall(r'\b([A-Z]{2,}\s+[A-Z]{2,})\b', self.cleaned_text)

    def extract_patient_sex(self):
        """Extrai o sexo do paciente."""
        match = re.search(r'\b(M|F)\b', self.cleaned_text)
        return match.group(1) if match else 'Não encontrado'

    def extract_exam_type(self):
        """Extrai o tipo de exame (quantidade de canais)."""
        match = re.search(r'Holter de (\d+) canais', self.cleaned_text)
        return match.group(1) if match else 'Não encontrado'

    def extract_exam_duration(self):
        """Extrai a duração do exame em horas."""
        match = re.search(r'HRS:(\d+)', self.cleaned_text)
        return match.group(1) if match else 'Não encontrada'

    def extract_exam_config(self):
        """Extrai a configuração do exame."""
        match = re.search(r'(\d+\s+\d+\s+\d+\s+TP)', self.cleaned_text)
        return match.group(1) if match else 'Não encontrada'

    def extract_equipment(self):
        """Extrai o nome do equipamento utilizado."""
        match = re.search(r'(CardioLight|Ensicor)', self.cleaned_text)
        return match.group(1) if match else 'Não encontrado'

    def extract_file_path(self):
        """Extrai o caminho do arquivo do exame."""
        match = re.search(r'C:\\(.+?\.hfdp)', self.cleaned_text)
        return match.group(1) if match else 'Não encontrado'

def print_file_content(file_path, encoding='utf-8'):
    """Lê o conteúdo do arquivo e retorna as primeiras 5 linhas concatenadas."""
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()
            data = ''.join(line.strip() for line in lines[:5])  # Concatena as 5 primeiras linhas
            return data
    except UnicodeDecodeError:
        return f"Falha ao decodificar com {encoding}."
    except IOError as e:
        return f"Erro ao tentar ler o arquivo: {e}"

def return_data(file_path):
    """Testa diferentes codificações e retorna o conteúdo do arquivo."""
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'ascii']
    results = []

    # Testando diferentes codificações
    for encoding in encodings:
        content = print_file_content(file_path, encoding)
        results.append(f"Testando codificação: {encoding}\n{content}")

    # Usando chardet para detectar a codificação
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read(1000)  # Lê até 1000 bytes para detectar a codificação
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            if detected_encoding:
                detected_content = print_file_content(file_path, detected_encoding)
                results.append(f"Codificação detectada: {detected_encoding}\n{detected_content}")
    except IOError as e:
        results.append(f"Erro ao tentar detectar a codificação: {e}")

    # Tentativa de verificar se é um arquivo comprimido (exemplo com zip)
    try:
        import zipfile
        if zipfile.is_zipfile(file_path):
            results.append("O arquivo parece ser um zip.")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_contents = "Conteúdo do zip (primeiras 5 entradas):\n"
                for i, name in enumerate(zip_ref.namelist()[:5]):
                    zip_contents += f"{i+1}: {name}\n"
                results.append(zip_contents)
        else:
            results.append("O arquivo não é um zip.")
    except ImportError:
        results.append("Módulo zipfile não está disponível.")

    # Retorna todas as strings coletadas
    return "\n".join(results)

def decodeXCM(filepath):
    data = return_data(filepath)
    extractor = AdvancedMedicalReportExtractor(data)
    print('dados: ',data)
    print(extractor.extract_doctors())
    print(extractor.extract_equipment())
    print(extractor.extract_patient_names())
    print(extractor.extract_exam_type())
    print(extractor.extract_patient_sex())
    return data