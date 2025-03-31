import os
import pdfplumber

def pdf_to_txt(pdf_path, txt_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()

        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"成功转换: {pdf_path} -> {txt_path}")
    except Exception as e:
        print(f"转换 {pdf_path} 时出错: {e}")

def convert_pdfs_in_directory(source_dir, target_dir):
    for root, dirs, files in os.walk(source_dir):
        # 计算相对于源目录的相对路径
        relative_path = os.path.relpath(root, source_dir)
        # 构建目标目录
        target_sub_dir = os.path.join(target_dir, relative_path)
        # 创建目标子目录（如果不存在）
        if not os.path.exists(target_sub_dir):
            os.makedirs(target_sub_dir)

        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                # 生成对应的 TXT 文件名
                txt_file = os.path.splitext(file)[0] + '.txt'
                txt_path = os.path.join(target_sub_dir, txt_file)
                # 进行 PDF 到 TXT 的转换
                pdf_to_txt(pdf_path, txt_path)

# 源目录
source_directory = 'saves'
# 目标目录
target_directory = 'txt_saves'

# 调用函数进行转换
convert_pdfs_in_directory(source_directory, target_directory)