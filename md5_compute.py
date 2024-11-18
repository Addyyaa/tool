import sys
import hashlib
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QWidget, QMessageBox

class MD5Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MD5 计算工具")
        self.setGeometry(300, 300, 400, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 标签
        self.label = QLabel("请选择一个文件以计算其 MD5 值：")
        layout.addWidget(self.label)

        # 选择文件按钮
        self.select_file_button = QPushButton("选择文件")
        self.select_file_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_file_button)

        # 显示文件路径
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("文件路径将在这里显示")
        self.file_path_input.setReadOnly(True)
        layout.addWidget(self.file_path_input)

        # 计算 MD5 按钮
        self.calculate_md5_button = QPushButton("计算 MD5")
        self.calculate_md5_button.clicked.connect(self.calculate_md5)
        layout.addWidget(self.calculate_md5_button)

        # 显示 MD5 值
        self.md5_output = QLineEdit()
        self.md5_output.setPlaceholderText("MD5 值将在这里显示")
        self.md5_output.setReadOnly(True)
        layout.addWidget(self.md5_output)

        # 复制 MD5 按钮
        self.copy_button = QPushButton("复制 MD5")
        self.copy_button.clicked.connect(self.copy_md5)
        layout.addWidget(self.copy_button)

        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.file_path_input.setText(file_path)
        else:
            self.file_path_input.clear()

    def calculate_md5(self):
        file_path = self.file_path_input.text()
        if not file_path:
            QMessageBox.warning(self, "错误", "请先选择一个文件！")
            return
        try:
            md5_hash = self.compute_md5(file_path)
            self.md5_output.setText(md5_hash)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法计算 MD5 值：{str(e)}")

    def copy_md5(self):
        md5_value = self.md5_output.text()
        if md5_value:
            QApplication.clipboard().setText(md5_value)
            QMessageBox.information(self, "成功", "MD5 值已复制到剪贴板！")
        else:
            QMessageBox.warning(self, "错误", "没有可复制的 MD5 值！")

    @staticmethod
    def compute_md5(file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MD5Calculator()
    window.show()
    sys.exit(app.exec_())
