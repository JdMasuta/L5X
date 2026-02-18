#!/usr/bin/env python3
"""
L5X Mermaid GUI

A graphical user interface for the L5X state diagram generator.
Provides drag-and-drop functionality for .L5X files and generates Mermaid flowcharts.

Author: Generated with Claude Code
"""

import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    When PyInstaller bundles the app, it extracts files to a temporary folder
    and stores the path in sys._MEIPASS. This function returns the correct path
    whether running from source or as a bundled executable.

    Args:
        relative_path: Relative path to the resource file

    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment (development)
        base_path = Path(__file__).parent

    return Path(base_path) / relative_path


# Stylesheet for the application
STYLESHEET = """
QMainWindow {
    background-color: #64CCC9;
}

QLabel {
    font-size: 11pt;
}

#dropZone {
    background-color: white;
    border: 2px dashed #aaa;
    border-radius: 8px;
    padding: 10px;
    color: #666;
    font-size: 13pt;
}

#dropZoneHover {
    border: 2px dashed #4CAF50;
    color: #4CAF50;
}

QPushButton {
    background-color: #00a0dd;
    color: white;
    border: none;
    padding: 10px 20px;
    font-size: 11pt;
    border-radius: 4px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #45a049;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

#browseButton {
    background-color: #2196F3;
    max-width: 40px;
    padding: 8px;
}

#browseButton:hover {
    background-color: #0b7dda;
}

QLineEdit {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 10pt;
    background-color: white;
}

#statusBox {
    background-color: #f9f9f9;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    font-family: monospace;
    font-size: 9pt;
}
"""


class DropZoneWidget(QLabel):
    """Custom label widget that accepts drag and drop of .L5X files."""

    fileDropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Drag & Drop .L5X File Here\n\n(or click to browse)")
        self.setMinimumHeight(120)

        # Make clickable
        self.setMouseTracking(True)

    def dragEnterEvent(self, event):
        """Handle drag enter event - check if file is .L5X"""
        if event.mimeData().hasUrls():
            # Check if any URL ends with .L5X (case-insensitive)
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.upper().endswith('.L5X'):
                    event.accept()
                    self.setObjectName("dropZoneHover")
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event - reset styling"""
        self.setObjectName("dropZone")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        """Handle drop event - emit signal with file path"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        l5x_files = [f for f in files if f.upper().endswith('.L5X')]
        if l5x_files:
            self.fileDropped.emit(l5x_files[0])

        self.setObjectName("dropZone")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        """Handle mouse click - open file browser"""
        if event.button() == Qt.LeftButton:
            self.parent().parent().browse_input_file()


class L5XMermaidGUI(QMainWindow):
    """Main application window for L5X Mermaid diagram generator."""

    def __init__(self):
        super().__init__()
        self.input_file = None
        self.output_file = None
        self.initUI()

    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle('L5X Mermaid')
        self.setFixedSize(600, 650)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title - uses generic sans-serif font for cross-platform compatibility
        title = QLabel('L5X Mermaid - A State Diagram Generator')
        title_font = QFont()
        title_font.setStyleHint(QFont.SansSerif)  # Let Qt choose best sans-serif
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Drop zone
        self.drop_zone = DropZoneWidget()
        self.drop_zone.fileDropped.connect(self.on_file_dropped)
        main_layout.addWidget(self.drop_zone)

        # Tag name input
        tag_label = QLabel('Tag Name (optional):')
        main_layout.addWidget(tag_label)

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText('Leave empty to auto-detect')
        main_layout.addWidget(self.tag_input)

        # Output file selection
        output_label = QLabel('Output File:')
        main_layout.addWidget(output_label)

        output_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.output_input.setPlaceholderText('Select output file location...')
        output_layout.addWidget(self.output_input)

        browse_btn = QPushButton('📁')
        browse_btn.setObjectName('browseButton')
        browse_btn.setToolTip('Browse for output location')
        browse_btn.clicked.connect(self.browse_output_file)
        output_layout.addWidget(browse_btn)

        main_layout.addLayout(output_layout)

        # Generate button
        self.generate_btn = QPushButton('Generate Diagram')
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_diagram)
        main_layout.addWidget(self.generate_btn)

        # Status output box
        status_label = QLabel('Status:')
        main_layout.addWidget(status_label)

        self.status_box = QTextEdit()
        self.status_box.setObjectName('statusBox')
        self.status_box.setReadOnly(True)
        self.status_box.setMinimumHeight(150)
        self.status_box.setPlainText('Ready to process...')
        main_layout.addWidget(self.status_box)

        central_widget.setLayout(main_layout)

        # Apply stylesheet
        self.setStyleSheet(STYLESHEET)

    def on_file_dropped(self, filepath):
        """Handle file drop/selection event."""
        self.input_file = filepath
        filename = Path(filepath).name

        # Update drop zone
        self.drop_zone.setText(f'✓ {filename}\n\n(click to change)')

        # Auto-generate output file path
        default_output = Path(filepath).with_name(
            f'{Path(filepath).stem}_state_diagram.md'
        )
        self.output_file = str(default_output)
        self.output_input.setText(str(default_output))

        # Enable generate button
        self.generate_btn.setEnabled(True)

        # Update status
        self.clear_status()
        self.add_status(f'Loaded: {filename}', 'success')
        self.add_status('✓ Input file ready', 'info')

    def browse_input_file(self):
        """Open file dialog to select input .L5X file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            'Select L5X File',
            '',
            'L5X Files (*.L5X);;All Files (*)'
        )

        if filepath:
            self.on_file_dropped(filepath)

    def browse_output_file(self):
        """Open save file dialog to select output location."""
        default_name = ''
        if self.input_file:
            default_name = str(Path(self.input_file).with_name(
                f'{Path(self.input_file).stem}_state_diagram.md'
            ))

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            'Save Diagram As',
            default_name,
            'Markdown Files (*.md);;All Files (*)'
        )

        if filepath:
            self.output_file = filepath
            self.output_input.setText(filepath)
            self.add_status(f'Output will be saved to: {Path(filepath).name}', 'info')

    def clear_status(self):
        """Clear the status box."""
        self.status_box.clear()

    def add_status(self, message, level='info'):
        """
        Add a message to the status box with appropriate coloring.

        Args:
            message: The message to display
            level: Message level ('info', 'success', 'error', 'warning')
        """
        colors = {
            'info': '#333333',
            'success': '#4CAF50',
            'error': '#f44336',
            'warning': '#ff9800'
        }

        color = colors.get(level, colors['info'])

        # Add timestamp for non-info messages
        if level in ['success', 'error']:
            import datetime
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            message = f'[{timestamp}] {message}'

        self.status_box.append(f'<span style="color: {color};">{message}</span>')

        # Auto-scroll to bottom
        scrollbar = self.status_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def generate_diagram(self):
        """Generate the Mermaid diagram by calling the CLI script."""
        # Validate inputs
        if not self.input_file:
            self.add_status('✗ No input file selected', 'error')
            return

        if not self.output_file:
            self.add_status('✗ No output file selected', 'error')
            return

        # Clear previous status and start
        self.clear_status()
        self.add_status('Starting diagram generation...', 'info')
        self.add_status(f'Input: {Path(self.input_file).name}', 'info')
        self.add_status(f'Output: {Path(self.output_file).name}', 'info')

        # Get tag name if provided
        tag_name = self.tag_input.text().strip()
        if tag_name:
            self.add_status(f'Using tag: {tag_name}', 'info')

        # Disable generate button during processing
        self.generate_btn.setEnabled(False)
        self.add_status('', 'info')  # Blank line

        try:
            # Run the CLI script
            result = self.run_l5x_generator(
                self.input_file,
                self.output_file,
                tag_name if tag_name else None
            )

            # Process output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        self.add_status(line, 'info')

            # Check result
            if result.returncode == 0:
                self.add_status('', 'info')  # Blank line
                self.add_status(f'✓ Success! Diagram saved to: {self.output_file}', 'success')
            else:
                # Show errors
                if result.stderr:
                    self.add_status('', 'info')  # Blank line
                    for line in result.stderr.strip().split('\n'):
                        if line:
                            self.add_status(f'✗ {line}', 'error')
                else:
                    self.add_status('✗ Error: Process failed', 'error')

        except Exception as e:
            self.add_status('', 'info')  # Blank line
            self.add_status(f'✗ Error: {str(e)}', 'error')

        finally:
            # Re-enable generate button
            self.generate_btn.setEnabled(True)

    def run_l5x_generator(self, input_file, output_file, tag_name=None):
        """
        Run the L5X state diagram generator as a subprocess.

        Args:
            input_file: Path to input .L5X file
            output_file: Path to output .md file
            tag_name: Optional tag name

        Returns:
            subprocess.CompletedProcess object
        """
        script_path = get_resource_path('l5x_state_diagram.py')

        cmd = [sys.executable, str(script_path), input_file, '-o', output_file]
        if tag_name:
            cmd.extend(['-t', tag_name])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=None  # Use current working directory, not bundled temp folder
        )

        return result


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)

    # Set application-wide font - uses generic sans-serif for cross-platform compatibility
    font = QFont()
    font.setStyleHint(QFont.SansSerif)  # Let Qt choose best sans-serif for the platform
    font.setPointSize(10)
    app.setFont(font)

    window = L5XMermaidGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
