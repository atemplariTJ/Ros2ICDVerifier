import sys
import os
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    # macOS Conda + Pip PyQt6 plugin workaround
    if sys.platform == "darwin":
        import site
        # Find site-packages in the current environment
        for p in site.getsitepackages():
            plugin_path = os.path.join(p, "PyQt6", "Qt6", "plugins", "platforms")
            if os.path.exists(plugin_path):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
                break

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()