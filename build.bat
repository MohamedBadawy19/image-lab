@echo off
pip install -r requirements-dev.txt
pyinstaller --noconfirm --windowed --name ImageLab main.py
echo Done. Run dist\ImageLab\ImageLab.exe
